import cv2
import numpy as np
import os
import logging
import uuid
from typing import Optional, Dict, Any, List
from app.core.config import settings
from app.services.s3 import s3_service
import asyncio
from pathlib import Path

logger = logging.getLogger(__name__)


class SketchConverter:
    """
    A class for converting images to high-quality, realistic pencil sketches.
    Implements multiple techniques to achieve pixel-perfect results.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the SketchConverter with configuration parameters.

        Args:
            config: Dictionary containing configuration parameters for sketch conversion.
                   If None, default parameters will be used.
        """
        self.config = config or {
            # Default parameters for basic sketch
            "sigma_s": 60,  # Structure preserving parameter
            "sigma_r": 0.07,  # Detail preserving parameter
            "shade_factor": 0.05,  # Controls the pencil shade intensity
            # Parameters for advanced sketch
            "kernel_size": 21,
            "blur_type": "gaussian",  # Options: "gaussian", "median", "bilateral"
            "edge_preserve": True,
            "texture_enhance": True,
            "contrast": 1.5,
            "brightness": 0,
            "smoothing_factor": 0.9,
        }

        # Create temp directory if it doesn't exist
        os.makedirs(settings.temp_dir, exist_ok=True)
    
    
    
    def basic_sketch(self, image: np.ndarray) -> np.ndarray:
        """
        Create a basic pencil sketch using simple techniques.
        This produces a clean, simple sketch with good contrast.

        Args:
            image: Input image in BGR format

        Returns:
            Pencil sketch image
        """
        try:
            # Convert to grayscale
            gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Invert the grayscale image
            inverted_image = 255 - gray_image

            # Apply Gaussian blur to the inverted image
            blurred_image = cv2.GaussianBlur(inverted_image, (21, 21), 0)

            # Invert the blurred image back
            inverted_blurred = 255 - blurred_image

            # Create the pencil sketch using color dodge blend
            # Avoid division by zero by adding small epsilon
            inverted_blurred_safe = inverted_blurred.astype(np.float32) + 1e-7
            gray_float = gray_image.astype(np.float32)
            
            # Apply dodge blend: min(base * 255 / (255 - blend), 255)
            sketch = np.minimum(gray_float * 255.0 / inverted_blurred_safe, 255.0)
            
            # Convert back to uint8
            sketch = sketch.astype(np.uint8)
            
            # Enhance contrast slightly for better visibility
            sketch = cv2.convertScaleAbs(sketch, alpha=1.2, beta=10)

            return sketch
            
        except Exception as e:
            logger.error(f"Error in basic_sketch: {e}")
            # Fallback: return a simple edge-detected version
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 9)

    def advanced_sketch(self, image: np.ndarray) -> np.ndarray:
        """
        Create a high-quality, realistic pencil sketch with better detail preservation.

        Args:
            image: Input image in BGR format

        Returns:
            High-quality pencil sketch image
        """
        try:
            # Ensure we have a valid image
            if image is None or image.size == 0:
                raise ValueError("Invalid input image")

            # Convert to grayscale if the image is color
            if len(image.shape) == 3 and image.shape[2] == 3:
                gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray_image = image.copy()

            # Step 1: Apply bilateral filter to reduce noise while keeping edges sharp
            bilateral = cv2.bilateralFilter(gray_image, 9, 80, 80)
            
            # Step 2: Create inverted image
            inverted = 255 - bilateral
            
            # Step 3: Apply Gaussian blur to inverted image
            blur_kernel = max(21, min(51, gray_image.shape[0] // 20))  # Adaptive kernel size
            if blur_kernel % 2 == 0:
                blur_kernel += 1
            blurred = cv2.GaussianBlur(inverted, (blur_kernel, blur_kernel), 0)
            
            # Step 4: Apply color dodge blend mode
            sketch = self._improved_color_dodge(bilateral, blurred)
            
            # Step 5: Enhance edges for more pencil-like appearance
            edges = cv2.Laplacian(gray_image, cv2.CV_8U, ksize=3)
            edges = cv2.GaussianBlur(edges, (3, 3), 0)
            
            # Combine sketch with subtle edge enhancement
            sketch_float = sketch.astype(np.float32)
            edges_float = edges.astype(np.float32)
            
            # Blend edges into sketch
            enhanced = sketch_float - (edges_float * 0.3)
            enhanced = np.clip(enhanced, 0, 255).astype(np.uint8)
            
            # Step 6: Final contrast and brightness adjustment
            enhanced = cv2.convertScaleAbs(enhanced, alpha=1.1, beta=5)
            
            return enhanced

        except Exception as e:
            logger.error(f"Error in advanced_sketch: {e}")
            # Fallback to basic sketch
            return self.basic_sketch(image)

    def artistic_sketch(self, image: np.ndarray) -> np.ndarray:
        """
        Create an artistic pencil sketch with crosshatching-like texture and varied line weights.

        Args:
            image: Input image in BGR format

        Returns:
            Artistic pencil sketch image
        """
        try:
            # Ensure we have a valid image
            if image is None or image.size == 0:
                raise ValueError("Invalid input image")

            # Convert to grayscale if needed
            if len(image.shape) == 3 and image.shape[2] == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()

            # Step 1: Create base sketch using dodge blend
            inverted = 255 - gray
            blurred = cv2.GaussianBlur(inverted, (25, 25), 0)
            base_sketch = self._improved_color_dodge(gray, blurred)
            
            # Step 2: Create multiple edge layers for artistic effect
            # Fine edges
            fine_edges = cv2.Canny(gray, 50, 150)
            fine_edges = cv2.GaussianBlur(fine_edges, (3, 3), 0)
            
            # Coarse edges
            coarse_edges = cv2.Canny(gray, 30, 80)
            coarse_edges = cv2.dilate(coarse_edges, np.ones((2, 2), np.uint8), iterations=1)
            coarse_edges = cv2.GaussianBlur(coarse_edges, (3, 3), 0)
            
            # Step 3: Create texture using different directional filters
            # Horizontal texture
            kernel_h = np.array([[-1, -1, -1],
                                [ 2,  2,  2],
                                [-1, -1, -1]], dtype=np.float32) / 3
            texture_h = cv2.filter2D(gray, -1, kernel_h)
            texture_h = np.abs(texture_h).astype(np.uint8)
            
            # Vertical texture
            kernel_v = np.array([[-1, 2, -1],
                                [-1, 2, -1],
                                [-1, 2, -1]], dtype=np.float32) / 3
            texture_v = cv2.filter2D(gray, -1, kernel_v)
            texture_v = np.abs(texture_v).astype(np.uint8)
            
            # Combine textures
            texture_combined = cv2.bitwise_or(texture_h, texture_v)
            texture_combined = cv2.GaussianBlur(texture_combined, (3, 3), 0)
            
            # Step 4: Blend all components together
            base_float = base_sketch.astype(np.float32)
            fine_float = fine_edges.astype(np.float32)
            coarse_float = coarse_edges.astype(np.float32)
            texture_float = texture_combined.astype(np.float32)
            
            # Create artistic blend
            artistic = base_float.copy()
            
            # Add fine edges (subtle)
            artistic = artistic - (fine_float * 0.2)
            
            # Add coarse edges (more prominent)
            artistic = artistic - (coarse_float * 0.4)
            
            # Add texture (very subtle)
            artistic = artistic - (texture_float * 0.1)
            
            # Ensure valid range
            artistic = np.clip(artistic, 0, 255).astype(np.uint8)
            
            # Step 5: Apply unsharp masking for better definition
            gaussian = cv2.GaussianBlur(artistic, (5, 5), 0)
            unsharp_mask = cv2.addWeighted(artistic, 1.5, gaussian, -0.5, 0)
            unsharp_mask = np.clip(unsharp_mask, 0, 255).astype(np.uint8)
            
            # Step 6: Final adjustments
            result = cv2.convertScaleAbs(unsharp_mask, alpha=1.15, beta=8)
            
            return result

        except Exception as e:
            logger.error(f"Error in artistic_sketch: {e}")
            # Fallback to basic sketch
            return self.basic_sketch(image)

    def _improved_color_dodge(self, base: np.ndarray, blend: np.ndarray) -> np.ndarray:
        """
        Improved color dodge blend mode that produces better sketch effects.

        Args:
            base: Base grayscale image
            blend: Blend grayscale image (usually blurred inverted)

        Returns:
            Blended image with dodge effect
        """
        try:
            # Ensure same dimensions
            if base.shape != blend.shape:
                blend = cv2.resize(blend, (base.shape[1], base.shape[0]))

            # Convert to float for precise calculations
            base_float = base.astype(np.float32)
            blend_float = blend.astype(np.float32)

            # Apply color dodge formula: base / (255 - blend) * 255
            # Handle division by zero cases
            denominator = 255.0 - blend_float
            denominator = np.where(denominator == 0, 0.1, denominator)  # Avoid division by zero
            
            result = (base_float / denominator) * 255.0
            
            # Handle overflow cases where blend is very close to 255
            overflow_mask = blend_float > 254
            result = np.where(overflow_mask, 255.0, result)
            
            # Ensure valid range
            result = np.clip(result, 0, 255).astype(np.uint8)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in _improved_color_dodge: {e}")
            return base.copy()

    def _dodge_and_burn(self, inverted: np.ndarray, gray: np.ndarray) -> np.ndarray:
        """
        Apply dodge and burn effect to create a realistic pencil sketch.
        This method is now simplified and more reliable.

        Args:
            inverted: Inverted image
            gray: Original grayscale image

        Returns:
            Image with dodge and burn effect applied
        """
        try:
            # Ensure images have the same dimensions
            if inverted.shape != gray.shape:
                inverted = cv2.resize(inverted, (gray.shape[1], gray.shape[0]))

            # Use the improved color dodge method
            return self._improved_color_dodge(gray, inverted)
            
        except Exception as e:
            logger.error(f"Error in _dodge_and_burn: {e}")
            return gray.copy()

    def _enhance_texture(self, image: np.ndarray) -> np.ndarray:
        """
        Enhanced texture method that preserves sketch quality.

        Args:
            image: Input sketch image

        Returns:
            Texture-enhanced sketch
        """
        try:
            # Ensure input is uint8
            if image.dtype != np.uint8:
                image = np.clip(image, 0, 255).astype(np.uint8)
                
            # Apply gentle bilateral filter
            bilateral = cv2.bilateralFilter(image, 5, 50, 50)
            
            # Extract high-frequency details
            detail = cv2.subtract(image.astype(np.float32), bilateral.astype(np.float32))
            
            # Enhance details moderately
            enhanced_detail = detail * 1.5
            
            # Add back to bilateral filtered image
            result = bilateral.astype(np.float32) + enhanced_detail
            
            # Ensure valid range
            result = np.clip(result, 0, 255).astype(np.uint8)

            return result
            
        except Exception as e:
            logger.error(f"Error in _enhance_texture: {e}")
            return image
    def _adjust_contrast(self, image: np.ndarray, contrast_factor: float) -> np.ndarray:
        """
        Adjust the contrast of an image.

        Args:
            image: Input image
            contrast_factor: Contrast adjustment factor

        Returns:
            Contrast-adjusted image
        """
        # Apply contrast adjustment
        f = 131 * (contrast_factor + 1) / (127 * (131 - contrast_factor))
        alpha_c = f
        gamma_c = 127 * (1 - f)

        return cv2.addWeighted(image, alpha_c, image, 0, gamma_c)

class SketchService:
    """Service for converting images to pencil sketches."""

    def __init__(self):
        """Initialize the sketch service."""
        self.converter = SketchConverter()

    async def process_image(
        self,
        input_key: str,
        method: str = "advanced",
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process an image from S3 and convert it to a pencil sketch.

        Args:
            input_key: The S3 key of the input image
            method: The sketch method to use (basic, advanced, or artistic)
            config: Optional configuration parameters for the sketch conversion

        Returns:
            Dictionary containing the S3 key of the processed image and status
        """
        # Generate unique IDs for temporary files
        temp_id = str(uuid.uuid4())
        input_path = os.path.join(settings.temp_dir, f"input_{temp_id}.png")
        print("input_path", input_path)
        output_path = os.path.join(settings.temp_dir, f"output_{temp_id}.png")
        print("output_path", output_path)

        try:
            # Download the input image from S3
            download_success = await s3_service.download_file(input_key, input_path)
            if not download_success:
                return {
                    "success": False,
                    "error": "Failed to download input image from S3"
                }

            # Read the input image
            image = cv2.imread(input_path)
            if image is None:
                return {
                    "success": False,
                    "error": "Failed to read input image"
                }

            # Update converter config if provided
            if config:
                self.converter.config.update(config)

            # Apply the selected sketch method
            if method == "basic":
                sketch = self.converter.basic_sketch(image)
            elif method == "advanced":
                sketch = self.converter.advanced_sketch(image)
            elif method == "artistic":
                sketch = self.converter.artistic_sketch(image)
            else:
                return {
                    "success": False,
                    "error": f"Unknown sketch method: {method}"
                }

            # Save the sketch to a temporary file
            cv2.imwrite(output_path, sketch)

            # Generate output key based on input key
            input_path_obj = Path(input_key)
            output_key = f"{input_path_obj.stem}_sketch{input_path_obj.suffix}"

            # If input key has a directory structure, preserve it
            if "/" in input_key:
                directory = os.path.dirname(input_key)
                output_key = f"{directory}/{output_key}"

            # Upload the sketch to S3
            upload_success = await s3_service.upload_file(
                output_path,
                output_key,
                content_type="image/png",
                is_public=True
            )

            if not upload_success:
                return {
                    "success": False,
                    "error": "Failed to upload sketch to S3"
                }

            # Generate a presigned URL for the sketch
            download_url = await s3_service.get_presigned_download_url(output_key)

            return {
                "success": True,
                "input_key": input_key,
                "output_key": output_key,
                "method": method,
                "download_url": download_url
            }

        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            # Clean up temporary files
            try:
                if os.path.exists(input_path):
                    os.remove(input_path)
                if os.path.exists(output_path):
                    os.remove(output_path)
            except Exception as e:
                logger.error(f"Error cleaning up temporary files: {str(e)}")

    async def batch_process_images(
        self,
        input_keys: List[str],
        method: str = "advanced",
        config: Optional[Dict[str, Any]] = None,
        max_concurrency: int = 5
    ) -> Dict[str, Any]:
        """
        Process multiple images in batch.

        Args:
            input_keys: List of S3 keys for input images
            method: The sketch method to use
            config: Optional configuration parameters
            max_concurrency: Maximum number of concurrent conversions

        Returns:
            Dictionary containing results for each processed image
        """
        # Create a semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrency)

        async def process_with_semaphore(key):
            async with semaphore:
                return await self.process_image(key, method, config)

        # Create tasks for all images
        tasks = [process_with_semaphore(key) for key in input_keys]

        # Wait for all tasks to complete
        batch_results = await asyncio.gather(*tasks)

        # Compile results
        success_count = sum(1 for result in batch_results if result.get("success", False))

        return {
            "success": True,
            "total": len(input_keys),
            "successful": success_count,
            "failed": len(input_keys) - success_count,
            "results": batch_results
        }


# Create a singleton instance
sketch_service = SketchService()

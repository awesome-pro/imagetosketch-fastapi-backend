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
        os.makedirs(settings.TEMP_DIR, exist_ok=True)

    def basic_sketch(self, image: np.ndarray) -> np.ndarray:
        """
        Create a basic pencil sketch using simple techniques.

        Args:
            image: Input image in BGR format

        Returns:
            Pencil sketch image
        """
        # Convert to grayscale
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Invert the grayscale image
        inverted_image = 255 - gray_image

        # Apply Gaussian blur
        blurred_image = cv2.GaussianBlur(inverted_image, (21, 21), 0)

        # Invert the blurred image
        inverted_blurred = 255 - blurred_image

        # Create the pencil sketch by dividing the grayscale image by the inverted blurred image
        sketch = cv2.divide(gray_image, inverted_blurred, scale=256.0)

        return sketch

    def advanced_sketch(self, image: np.ndarray) -> np.ndarray:
        """
        Create a high-quality, realistic pencil sketch using advanced techniques.

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
                # If already grayscale, use as is
                gray_image = image.copy()

            # Apply edge-preserving filter for more natural look
            if self.config["edge_preserve"]:
                try:
                    # Using Domain Transform Filter for edge-preserving smoothing
                    filtered = cv2.edgePreservingFilter(
                        gray_image,
                        flags=cv2.NORMCONV_FILTER,
                        sigma_s=self.config["sigma_s"],
                        sigma_r=self.config["sigma_r"]
                    )
                except Exception as e:
                    logger.warning(f"Edge-preserving filter failed: {e}. Using fallback.")
                    filtered = gray_image
            else:
                filtered = gray_image

            # Apply blur based on configuration
            kernel_size = self.config["kernel_size"]
            # Ensure kernel size is odd
            if kernel_size % 2 == 0:
                kernel_size += 1

            try:
                if self.config["blur_type"] == "gaussian":
                    blurred = cv2.GaussianBlur(filtered, (kernel_size, kernel_size), 0)
                elif self.config["blur_type"] == "median":
                    blurred = cv2.medianBlur(filtered, kernel_size)
                elif self.config["blur_type"] == "bilateral":
                    d = kernel_size
                    blurred = cv2.bilateralFilter(filtered, d, d*2, d/2)
                else:
                    blurred = filtered
            except Exception as e:
                logger.warning(f"Blur operation failed: {e}. Using original image.")
                blurred = filtered

            # Invert the image
            inverted = 255 - blurred

            # Apply dodging and burning effect (similar to traditional darkroom technique)
            sketch = self._dodge_and_burn(inverted, gray_image)

            # Enhance contrast
            if self.config["contrast"] != 1.0:
                sketch = self._adjust_contrast(sketch, self.config["contrast"])

            # Apply texture enhancement if configured
            if self.config["texture_enhance"]:
                try:
                    sketch = self._enhance_texture(sketch)
                except Exception as e:
                    logger.warning(f"Texture enhancement failed: {e}. Skipping.")

            # Apply final smoothing if needed
            if self.config["smoothing_factor"] < 1.0:
                try:
                    smoothed = cv2.GaussianBlur(sketch, (5, 5), 0)
                    sketch = cv2.addWeighted(
                        sketch, 1 - self.config["smoothing_factor"],
                        smoothed, self.config["smoothing_factor"],
                        self.config["brightness"]
                    )
                except Exception as e:
                    logger.warning(f"Final smoothing failed: {e}. Skipping.")

            return sketch

        except Exception as e:
            logger.error(f"Error in advanced_sketch: {e}")
            # Fallback to basic sketch if advanced fails
            return self.basic_sketch(image)

    def artistic_sketch(self, image: np.ndarray) -> np.ndarray:
        """
        Create an artistic pencil sketch with more detail and texture.

        Args:
            image: Input image in BGR format

        Returns:
            Artistic pencil sketch image
        """
        try:
            # Ensure we have a valid image
            if image is None or image.size == 0:
                raise ValueError("Invalid input image")

            # Convert to grayscale if the image is color
            if len(image.shape) == 3 and image.shape[2] == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                # If already grayscale, use as is
                gray = image.copy()

            # Create negative image
            negative = 255 - gray

            # Apply Gaussian blur
            blur = cv2.GaussianBlur(negative, (21, 21), 0)

            # Blend using color dodge
            sketch = self._color_dodge(blur, gray)

            try:
                # Apply additional processing for artistic effect
                # Enhance edges
                edges = cv2.Laplacian(gray, cv2.CV_8U, ksize=5)
                edges = cv2.threshold(edges, 100, 255, cv2.THRESH_BINARY_INV)[1]

                # Ensure sketch and edges have the same dimensions and type
                if sketch.shape != edges.shape:
                    edges = cv2.resize(edges, (sketch.shape[1], sketch.shape[0]))

                # Convert both to the same data type
                sketch = sketch.astype(np.float32)
                edges = edges.astype(np.float32)

                # Combine sketch with edges
                sketch = cv2.addWeighted(sketch, 0.7, edges, 0.3, 0)

                # Apply slight sharpening
                kernel = np.array([[-1, -1, -1],
                                   [-1,  9, -1],
                                   [-1, -1, -1]])
                sketch = cv2.filter2D(sketch, -1, kernel)

                # Ensure values are within valid range for uint8
                sketch = np.clip(sketch, 0, 255).astype(np.uint8)
            except Exception as e:
                logger.warning(f"Artistic enhancement failed: {e}. Using basic dodge effect.")

            return sketch

        except Exception as e:
            logger.error(f"Error in artistic_sketch: {e}")
            # Fallback to basic sketch if artistic fails
            return self.basic_sketch(image)

    def _dodge_and_burn(self, inverted: np.ndarray, gray: np.ndarray) -> np.ndarray:
        """
        Apply dodge and burn effect to create a realistic pencil sketch.

        Args:
            inverted: Inverted image
            gray: Original grayscale image

        Returns:
            Image with dodge and burn effect applied
        """
        # Ensure images have the same dimensions
        if inverted.shape != gray.shape:
            inverted = cv2.resize(inverted, (gray.shape[1], gray.shape[0]))

        # Ensure the images are grayscale (single channel)
        if len(inverted.shape) > 2 and inverted.shape[2] > 1:
            inverted = cv2.cvtColor(inverted, cv2.COLOR_BGR2GRAY)
        if len(gray.shape) > 2 and gray.shape[2] > 1:
            gray = cv2.cvtColor(gray, cv2.COLOR_BGR2GRAY)

        # Avoid division by zero
        inverted_safe = np.clip(inverted, 0, 254)  # Ensure max value is 254 to avoid division by zero
        shade_factor = float(self.config["shade_factor"])

        # Dodge effect (lighten)
        dodge = cv2.divide(gray, 255 - inverted_safe, scale=256.0)

        # Burn effect (darken)
        # Add shade_factor to avoid division by zero
        burn = 255 - cv2.divide(255 - gray, inverted_safe + shade_factor, scale=256.0)

        # Combine dodge and burn
        result = cv2.addWeighted(dodge, 0.6, burn, 0.4, 0)

        return result

    def _color_dodge(self, blur: np.ndarray, gray: np.ndarray) -> np.ndarray:
        """
        Apply color dodge blend mode.

        Args:
            blur: Blurred image
            gray: Grayscale image

        Returns:
            Blended image
        """
        try:
            # Ensure images have the same dimensions
            if blur.shape != gray.shape:
                blur = cv2.resize(blur, (gray.shape[1], gray.shape[0]))

            # Ensure the images are grayscale (single channel)
            if len(blur.shape) > 2 and blur.shape[2] > 1:
                blur = cv2.cvtColor(blur, cv2.COLOR_BGR2GRAY)
            if len(gray.shape) > 2 and gray.shape[2] > 1:
                gray = cv2.cvtColor(gray, cv2.COLOR_BGR2GRAY)

            # Convert to float32 for safer arithmetic operations
            gray_float = gray.astype(np.float32)
            blur_float = blur.astype(np.float32)

            # Avoid division by zero by ensuring denominator is at least 1
            denominator = np.maximum(255.0 - blur_float, 1.0)

            # Apply color dodge formula: result = base / (255 - blend)
            # Use float arithmetic to avoid integer overflow
            result = gray_float * 255.0 / denominator

            # Clip values to valid range [0, 255]
            result = np.clip(result, 0, 255).astype(np.uint8)

            return result

        except Exception as e:
            logger.error(f"Error in _color_dodge: {e}")
            # Return original grayscale as fallback
            return gray.copy()

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

    def _enhance_texture(self, image: np.ndarray) -> np.ndarray:
        """
        Enhance texture details in the sketch.

        Args:
            image: Input sketch image

        Returns:
            Texture-enhanced sketch
        """
        # Apply bilateral filter to enhance edges while reducing noise
        bilateral = cv2.bilateralFilter(image, 9, 75, 75)

        # Extract detail layer
        detail = cv2.subtract(image, bilateral)
        # Enhance details
        enhanced_detail = cv2.multiply(detail, np.array([2], dtype=np.uint8))

        # Add enhanced details back to the image
        result = cv2.add(bilateral, enhanced_detail)

        return result


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
        input_path = os.path.join(settings.TEMP_DIR, f"input_{temp_id}.png")
        output_path = os.path.join(settings.TEMP_DIR, f"output_{temp_id}.png")

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

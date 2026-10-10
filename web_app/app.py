import os
from io import BytesIO
from time import perf_counter
from uuid import uuid4

import segno
from flask import Flask, jsonify, render_template, request, url_for
from PIL import Image, ImageOps

try:
    import cv2
    import numpy as np
except ImportError:  # QR decoding is optional
    cv2 = None
    np = None

from .algo_interface import ALGORITHM_MODULES

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'uploads')
app.config['OUTPUT_FOLDER'] = os.path.join(app.static_folder, 'output')

# Ensure folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)


# Route for the main page
@app.route('/')
def home():
    return render_template('dashboard.html')


# Route that returns the list of algorithms available
@app.route('/api/algorithm_list', methods=['GET'])
def get_algorithms():
    algorithms = {
        key: value["name"]
        for key, value in ALGORITHM_MODULES.items()
        if value.get("result_type") != "text"
    }
    return jsonify({"algorithms": algorithms})


@app.route('/text-share', methods=['GET', 'POST'])
def text_share():
    result = None
    error_message = None

    if request.method == 'POST':
        operation = request.form.get('operation')
        try:
            text_module = ALGORITHM_MODULES["tc_utf8_xor"]
            run_id = uuid4().hex

            if operation == "encryption":
                shares = text_module["encrypt"](request.form.get("text", ""))
                share_urls = []
                for index, share in enumerate(shares, start=1):
                    filename = f"text_{run_id}_share{index}.png"
                    share.save(os.path.join(app.config['OUTPUT_FOLDER'], filename))
                    share_urls.append(url_for('static', filename=f'output/{filename}'))
                result = {"operation": operation, "share_urls": share_urls}

            elif operation == "decryption":
                first_file = request.files.get("image1")
                second_file = request.files.get("image2")
                if (
                    not first_file
                    or not first_file.filename
                    or not second_file
                    or not second_file.filename
                ):
                    raise ValueError("Choose both text-share images before reconstructing the message.")

                with Image.open(first_file.stream) as first_image:
                    share_one = first_image.convert("L")
                with Image.open(second_file.stream) as second_image:
                    share_two = second_image.convert("L")
                decrypted_text = text_module["decrypt"](share_one, share_two)
                result = {"operation": operation, "text": decrypted_text}

            else:
                raise ValueError("Choose whether to create or reconstruct text shares.")
        except (OSError, ValueError) as error:
            error_message = str(error)

    return render_template("text_share.html", result=result, error_message=error_message)


COMPARE_MAX_SIZE = (128, 128)


@app.route('/text-qr', methods=['GET', 'POST'])
def text_qr():
    result = None
    error_message = None

    if request.method == 'POST':
        operation = request.form.get('operation')
        try:
            if operation == "generate":
                text = request.form.get("text", "")
                if not text.strip():
                    raise ValueError("Enter some text to convert into a QR code.")
                level = request.form.get("error_level", "M")
                if level not in ("L", "M", "Q", "H"):
                    level = "M"
                try:
                    qr = segno.make(text, error=level, encoding="utf-8")
                except segno.DataOverflowError as error:
                    raise ValueError("The text is too long to fit in a QR code.") from error
                filename = f"qr_{uuid4().hex}.png"
                qr.save(
                    os.path.join(app.config['OUTPUT_FOLDER'], filename),
                    scale=10, border=4, kind="png",
                )
                result = {
                    "operation": operation,
                    "qr_url": url_for('static', filename=f'output/{filename}'),
                }

            elif operation == "decode":
                if cv2 is None:
                    raise ValueError("QR decoding needs the 'opencv-python-headless' package.")
                uploaded_file = request.files.get("image")
                if not uploaded_file or not uploaded_file.filename:
                    raise ValueError("Choose a QR code image to decode.")
                with Image.open(uploaded_file.stream) as qr_image:
                    qr_image.load()
                    rgb = qr_image.convert("RGB")
                # A white margin helps the detector find codes cropped tightly.
                rgb = ImageOps.expand(rgb, border=max(rgb.size) // 10 + 10, fill="white")
                pixels = cv2.cvtColor(np.array(rgb), cv2.COLOR_RGB2BGR)
                decoded, _, _ = cv2.QRCodeDetector().detectAndDecode(pixels)
                if not decoded:
                    raise ValueError("No readable QR code was found in that image.")
                result = {"operation": operation, "text": decoded}

            else:
                raise ValueError("Choose whether to generate or decode a QR code.")
        except (OSError, ValueError) as error:
            error_message = str(error)

    return render_template("text_qr.html", result=result, error_message=error_message)


def _comparison_algorithms():
    return {
        key: module
        for key, module in ALGORITHM_MODULES.items()
        if module.get("result_type") != "text"
        and callable(module.get("encrypt"))
        and callable(module.get("decrypt"))
        and module.get("requirements", {}).get("encryption", {}).get("num_images") == 1
        and module.get("requirements", {}).get("decryption", {}).get("num_images") == 2
    }


def _default_parameters(module, operation):
    parameters = module.get("requirements", {}).get(operation, {}).get("parameters", {})
    values = []
    for key, config in parameters.items():
        if "default" in config:
            values.append(config["default"])
        elif config.get("type") == "select" and config.get("options"):
            values.append(config["options"][0])
        elif config.get("type") == "number":
            values.append(0)
        elif config.get("type") == "text":
            values.append("")
        else:
            raise ValueError(f"Cannot determine a default value for parameter '{key}'.")
    return values


def _png_size(image):
    buffer = BytesIO()
    _png_compatible(image).save(buffer, format="PNG")
    return buffer.tell()


def _png_compatible(image):
    return image.convert("RGB") if image.mode == "CMYK" else image


@app.route('/compare', methods=['GET', 'POST'])
def compare():
    algorithms = _comparison_algorithms()
    results = None
    error_message = None
    selected_algorithms = (
        request.form.getlist("algorithms")
        if request.method == "POST"
        else list(algorithms)
    )

    if request.method == "POST":
        try:
            uploaded_file = request.files.get("image")
            if not uploaded_file or not uploaded_file.filename:
                raise ValueError("Choose an image to compare the schemes.")

            selected_algorithms = list(dict.fromkeys(selected_algorithms))
            if not selected_algorithms:
                raise ValueError("Select at least one scheme to compare.")
            if any(key not in algorithms for key in selected_algorithms):
                raise ValueError("One or more selected schemes are not available for comparison.")

            with Image.open(uploaded_file.stream) as uploaded_image:
                uploaded_image.load()
                source_image = uploaded_image.copy()

            # The visual cryptography schemes are pure-Python per-pixel loops,
            # so large inputs would take minutes; benchmark on a bounded size.
            source_image.thumbnail(COMPARE_MAX_SIZE)

            run_id = uuid4().hex
            results = []
            for algorithm_key in selected_algorithms:
                module = algorithms[algorithm_key]
                image_type = module.get("image_type", "RGB")
                algorithm_image = source_image.convert(image_type)

                encryption_start = perf_counter()
                shares = module["encrypt"](
                    algorithm_image,
                    *_default_parameters(module, "encryption"),
                )
                encryption_ms = (perf_counter() - encryption_start) * 1000
                if not isinstance(shares, (tuple, list)) or len(shares) != 2:
                    raise ValueError(f"{module['name']} did not produce exactly two shares.")

                reconstruction_start = perf_counter()
                reconstructed = module["decrypt"](
                    *shares,
                    *_default_parameters(module, "decryption"),
                )
                reconstruction_ms = (perf_counter() - reconstruction_start) * 1000
                if not isinstance(reconstructed, Image.Image):
                    raise ValueError(f"{module['name']} did not produce an image reconstruction.")

                share_size = sum(_png_size(share) for share in shares)
                file_prefix = f"compare_{run_id}_{algorithm_key}"
                share_urls = []
                for index, share in enumerate(shares, start=1):
                    filename = f"{file_prefix}_share{index}.png"
                    _png_compatible(share).save(
                        os.path.join(app.config['OUTPUT_FOLDER'], filename)
                    )
                    share_urls.append(url_for('static', filename=f'output/{filename}'))

                reconstruction_filename = f"{file_prefix}_reconstruction.png"
                _png_compatible(reconstructed).save(
                    os.path.join(app.config['OUTPUT_FOLDER'], reconstruction_filename)
                )
                results.append({
                    "name": module["name"],
                    "encryption_ms": encryption_ms,
                    "reconstruction_ms": reconstruction_ms,
                    "share_size": share_size,
                    "share_urls": share_urls,
                    "reconstruction_url": url_for(
                        'static', filename=f'output/{reconstruction_filename}'
                    ),
                })
        except (OSError, ValueError) as error:
            error_message = str(error)
            results = None

    return render_template(
        "compare.html",
        algorithms=algorithms,
        selected_algorithms=selected_algorithms,
        results=results,
        error_message=error_message,
    )


# Route that returns the description of the indicated algorithm
@app.route('/api/algorithm_description/<algorithm>')
def get_algorithm_description(algorithm):
    module = ALGORITHM_MODULES.get(algorithm)
    if module and "description" in module:
        return jsonify(module["description"])

    return jsonify({"text": "Description not available.", "links": []})


# Route that returns the requirements of the indicated algorithm
@app.route('/api/algorithm_requirements/<algorithm>/<operation>', methods=['GET'])
def get_algorithm_requirements(algorithm, operation):
    try:
        # Check if the requested algorithm exists
        if algorithm not in ALGORITHM_MODULES:
            return jsonify({"error": "Algorithm not found"}), 404

        # Retrieve the algorithm's requirements
        requirements = ALGORITHM_MODULES[algorithm].get("requirements", {})

        # Check if the requested operation (encryption/decryption) exists
        if operation not in requirements:
            return jsonify({"error": "Invalid operation"}), 400

        # Extract the required number of input images and parameters
        operation_requirements = requirements[operation]
        num_images = operation_requirements.get("num_images", 1)
        parameters = operation_requirements.get("parameters", {})

        # Return the JSON response
        return jsonify({
            "num_images": num_images,
            "parameters": parameters
        })

    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": str(e)}), 500


# Process the selected operation
@app.route('/process', methods=['POST'])
def process():
    try:
        operation = request.form['operation']
        algorithm = request.form['algorithm']

        # Retrieve the algorithm module
        algorithm_module = ALGORITHM_MODULES.get(algorithm)
        if not algorithm_module:
            error_message = f"Unknown algorithm: {algorithm}"
            return render_template('error.html', error_message=error_message), 500

        # Retrieve algorithm requirements for the operation
        requirements = algorithm_module.get("requirements", {}).get(operation, {})
        num_images = requirements.get("num_images", 1)
        parameters = requirements.get("parameters", {})

        # Dynamically retrieve uploaded images based on num_images
        input_paths = []
        for i in range(1, num_images + 1):
            file = request.files.get(f"image{i}")
            if file and file.filename:
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(save_path)
                input_paths.append(save_path)

        # Ensure correct number of images
        if len(input_paths) != num_images:
            error_message = f"{operation.capitalize()} requires {num_images} image(s), but {len(input_paths)} provided."
            return render_template('error.html', error_message=error_message), 500

        # Open images
        images = [Image.open(path).convert(algorithm_module.get("image_type")) for path in input_paths]

        # Extract additional parameters from the form
        param_values = {}
        for param_key, param_config in parameters.items():
            if param_config["type"] == "number":
                param_values[param_key] = int(request.form.get(param_key, param_config.get("default", 0)))
            elif param_config["type"] == "select":
                param_values[param_key] = request.form.get(param_key, param_config.get("default"))
            elif param_config["type"] == "text":
                param_values[param_key] = request.form.get(param_key, param_config.get("default", ""))
            # Here it is possible to add other types of requirements for new schemes

        # Call the appropriate method dynamically
        if operation == "encryption":
            encrypt_method = algorithm_module.get("encrypt")
            result = encrypt_method(*images, *param_values.values())  # Pass images first, then only parameter values
            return save_and_render_shares(*result, extension=algorithm_module.get("extension"))

        elif operation == "decryption":
            decrypt_method = algorithm_module.get("decrypt")
            result = decrypt_method(*images, *param_values.values())  # Pass images first, then only parameter values
            if algorithm_module.get("result_type") == "text":
                return render_template('dec_result.html', decrypted_text=result)
            return save_and_render_decryption_result(result, algorithm_module.get("extension"))

    except Exception as e:
        error_message = str(e)
        return render_template('error.html', error_message=error_message), 500


def save_and_render_shares(*shares, extension, output_folder='output'):
    share_urls = []
    download_urls = []

    for i, share in enumerate(shares, start=1):
        filename = f"share{i}.{extension}"
        share_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)

        # Save shares
        share.save(share_path)

        # Generate URLs for rendering and downloading
        share_urls.append(url_for('static', filename=f'{output_folder}/{filename}'))
        download_urls.append(url_for('static', filename=f'{output_folder}/{filename}'))

    # Render results dynamically. This rendering handles the case where more than 2 shares are generated.
    return render_template(
        'enc_result.html',
        share_urls=share_urls,
        download_urls=download_urls,
        zip=zip  # For using zip in the loop of enc_result.html
    )


# Helper function to handle decryption and rendering results
def save_and_render_decryption_result(result_image, extension, output_folder='output'):
    result_path = os.path.join(app.config['OUTPUT_FOLDER'], f'decrypted.{extension}')
    result_image.save(result_path)

    # Render results
    return render_template(
        'dec_result.html',
        result_url=url_for('static', filename=f'{output_folder}/decrypted.{extension}'),
        result_download=url_for('static', filename=f'{output_folder}/decrypted.{extension}')
    )


if __name__ == '__main__':
    app.run(debug=True)

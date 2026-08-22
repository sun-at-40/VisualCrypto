## Overview
**VisualCrypto** is an open-source Python-based toolkit with a web interface designed for **Visual Secret Sharing (VSS)**, a cryptographic technique that splits a secret image into multiple shares. Each share appears as random noise and reveals no information on its own, but when combined, they reconstruct the original image.

This repository primarily focuses on **(2,2)-VSS schemes**, where a secret image is split into two shares, both of which are required to reveal the hidden content.


---

## Features
- Support for Visual Cryptography (VC) & Random Grid (RG) techniques
- Web-based & script-based execution for ease of use
- Easily extendable to incorporate new cryptographic schemes
- Reference-based implementation, ensuring that any scientific work derived from this repository maintains appropriate citations.

---

## Getting Started

### Installation  
Clone the repository and install dependencies:  
```bash
git clone https://github.com/coduri/VisualCrypto.git
cd VisualCrypto
python -m venv .venv
```

Activate the virtual environment:

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate
```

Install the project dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Usage  
You can interact with the toolkit in two ways:  
1. **Running Python scripts**
2. **Using the Web Interface**

📌 _For a step-by-step guide, check out the [User Guide](https://coduri.github.io/VisualCrypto/pages/getting_started/)._ 

---

## Web Interface  
Start the web interface from the repository root with:

```bash
python -m web_app.app
```

Then open `http://127.0.0.1:5000` in a browser. On Windows, if PowerShell prevents
environment activation, run the commands directly through the virtual environment:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m web_app.app
```

Below are sample screenshots of the **web-based interface** of VisualCrypto:

<div align="center">
    <img src="docs/assets/readme/web_enc1.png" alt="Web App Encryption 1" width="48%"> 
    <img src="docs/assets/readme/web_enc2.png" alt="Web App Encryption 2" width="48%"> 
</div>

<div align="center">
    <img src="docs/assets/readme/web_dec1.png" alt="Web App Decryption 1" width="48%"> 
    <img src="docs/assets/readme/web_dec2.png" alt="Web App Decryption 2" width="48%"> 
</div>

---

## Contributing
Contributions are welcome! 

If you’d like to implement a new Visual Secret Sharing algorithm or improve existing features, please check out our **[Contribution Guide](https://coduri.github.io/VisualCrypto/pages/contributing/)**.  

Before submitting a pull request, ensure that:  
- Your algorithm follows the required structure.  
- You’ve tested both encryption & decryption.  
- The web interface is correctly updated.  

Thank you for helping improve **VisualCrypto**! 🚀  

---

## Main References
- **Visual Cryptography**: Naor, Moni, and Adi Shamir. "Visual cryptography." *Advances in Cryptology—EUROCRYPT'94*. Springer, 1995. <a href="https://doi.org/10.1007/BFb0053419" target="_blank">DOI</a>
- **Random Grid**: Kafri, Oded, and Eliezer Keren. "Encryption of pictures and shapes by random grids." *Optics Letters* 12.6 (1987): 377-379. <a href="https://doi.org/10.1364/ol.12.000377" target="_blank">DOI</a>
  

---

## Citation
If you find this project useful for your research, please consider citing:

 ```bibtex
@misc{Coduri2025VisualCrypto,
    author = {Christian Coduri},
    title = {VisualCrypto: A Python-based toolkit for image-based secret sharing},
    year = {2025},
    publisher = {GitHub},
    url = {https://github.com/coduri/VisualCrypto},
    note = {GitHub repository}
}
 ```

---

## License
This project is licensed under the **MIT License**. See the [LICENSE](LICENSE.txt) file for details.

---

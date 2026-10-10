import glob, os, sys
from setuptools import setup, Extension
from setuptools.command.build_py import build_py as _build_py
from Cython.Build import cythonize

KEEP_PY = {"ocm/__init__.py", "ocm/__main__.py", "ocm/_r/__init__.py", "ocm/cmlm_vector/__init__.py", "ocm/providers/__init__.py"}
LINK = ["-Wl,-s"] if sys.platform.startswith("linux") else []   # strip symbols from Linux builds
COMPILED = sorted(p for p in glob.glob("ocm/**/*.py", recursive=True) if p not in KEEP_PY)


class build_py(_build_py):
    def find_package_modules(self, package, package_dir):  # ship no source for compiled modules
        return [m for m in super().find_package_modules(package, package_dir) if m[2].replace(os.sep, "/") in KEEP_PY]


setup(
    name="optimal-context-mapping",
    version="0.2.1",
    description="Optimal Context Mapping: evaluation build",
    author="Devieswar Kancheti",
    license="LicenseRef-Proprietary",
    license_files=["LICENSE", "THIRD_PARTY_NOTICES"],
    packages=["ocm", "ocm._r", "ocm.cmlm_vector", "ocm.providers"],
    package_data={"ocm": ["data/*.json"]},
    python_requires=">=3.10",
    install_requires=["numpy>=2.0", "torch>=2.1", "transformers>=4.40"],
    entry_points={"console_scripts": ["ocm = ocm.__main__:main"]},
    ext_modules=cythonize([os.path.splitext(p)[0].replace("/", ".") and Extension(os.path.splitext(p)[0].replace("/", "."), [p], extra_link_args=LINK) for p in COMPILED],
                          compiler_directives={"language_level": 3, "emit_code_comments": False, "embedsignature": False},
                          quiet=True),
    cmdclass={"build_py": build_py},
    zip_safe=False,
)

from setuptools import setup

if __name__ == "__main__":
    with open("requirements.txt", "r", encoding="utf-8") as file:
        requirements = [line.strip("\n") for line in file.readlines()]
    setup(install_requires=requirements)

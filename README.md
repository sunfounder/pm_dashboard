# Pironman Dashboard

Pironman Dashboard is a simple server that provides a REST API and host a web page to display the data from the Pironman Dashboard.

- [Pironman Dashboard](#pironman-dashboard)
  - [Installation](#installation)
  - [WWW](#www)
  - [About SunFounder](#about-sunfounder)
  - [Contact us](#contact-us)

## Installation

```bash
# Install development dependencies
apt-get -y install python3 python3-pip python3-venv git wget unzip
pip3 install build

# Clone the repository
git clone https://github.com/sunfounder/pm_dashboard.git

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Build the package
python3 -m build

# Install the package
pip3 install dist/*.whl
```

## WWW

This Package include a web page, located in `pm_dashboard/www` is a compiled web page from [Pironman Dashboard WWW](https://github.com/sunfounder/pm_dashboard_www) repository.

To update the web page, download the [latest release](https://github.com/sunfounder/pm_dashboard_www/releases/latest/download/www.zip)
```bash
wget https://github.com/sunfounder/pm_dashboard_www/releases/latest/download/www.zip
```
Unzip the file
```bash
unzip www.zip
```
Remove the old `www` folder
```bash
rm -r pm_dashboard/www
```
Copy the web page to the `pm_dashboard/www` directory
```bash
cp -r www pm_dashboard/www
```
Clean the files
```bash
rm www.zip
```

## About SunFounder
SunFounder is a company focused on STEAM education with products like open source robots, development boards, STEAM kit, modules, tools and other smart devices distributed globally. In SunFounder, we strive to help elementary and middle school students as well as hobbyists, through STEAM education, strengthen their hands-on practices and problem-solving abilities. In this way, we hope to disseminate knowledge and provide skill training in a full-of-joy way, thus fostering your interest in programming and making, and exposing you to a fascinating world of science and engineering. To embrace the future of artificial intelligence, it is urgent and meaningful to learn abundant STEAM knowledge.

## Contact us
website:
    www.sunfounder.com

E-mail:
    service@sunfounder.com

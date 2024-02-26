# Pironman Dashboard

Pironman Dashboard is a simple server that provides a REST API and host a web page to display the data from the Pironman Dashboard.

## Installation

```bash
# Install development dependencies
apt-get -y install python3 python3-pip python3-venv git wget unzip
pip3 install build

# Download dashboard www
wget https://github.com/sunfounder/pm_dashboard_client/releases/latest/download/pm_dashboard_www.zip
unzip pm_dashboard_www.zip
cp -r pm_dashboard_www/pm_dashboard_www /opt/pm_dashboard_client

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

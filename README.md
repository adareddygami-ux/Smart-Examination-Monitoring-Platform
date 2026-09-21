# Smart Examination Monitoring Platform

## Development of Smart Examination Monitoring Platform with Integrity Analysis & Reporting System

### Project Overview

The Smart Examination Monitoring Platform is a web-based application designed to support secure and monitored online examinations.

The system combines candidate authentication, identity verification, examination management, browser monitoring, webcam monitoring, suspicious activity detection, integrity analysis, and reporting.

### Key Features

* Candidate registration and authentication
* Identity verification using webcam
* Examination session management
* Browser activity monitoring
* Webcam-based monitoring
* Suspicious activity detection
* Integrity analysis
* Behaviour analysis using K-Means clustering
* Examination and integrity reporting

### Technology Stack

| Technology       | Purpose                     |
| ---------------- | --------------------------- |
| Python           | Application development     |
| Flask            | Web application framework   |
| Flask-SQLAlchemy | Database management         |
| SQLite           | Database storage            |
| OpenCV           | Camera and image processing |
| HTML             | Web page structure          |
| CSS              | User interface              |
| JavaScript       | Client-side interaction     |
| K-Means          | Behaviour analysis          |
| GitHub           | Source code management      |

### Project Structure

```text
Smart-Examination-Monitoring-Platform/
│
├── models/
├── routes/
├── static/
├── templates/
├── tests/
├── utils/
├── app.py
├── config.py
├── extensions.py
├── requirements.txt
├── README.md
└── LICENSE
```

### Installation

Create and activate a Python virtual environment, then install the required dependencies:

```bash
python -m venv .venv
```

For Windows:

```bash
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### Run the Project

Start the Flask application:

```bash
python app.py
```

Then open the local address displayed by Flask, commonly:

```text
http://127.0.0.1:5000
```

### Documentation

Detailed information about the system architecture, workflow, database design, diagrams, modules, testing, results, and other project details is available in the **Project Documentation**.

### License

This project is licensed under the MIT License.

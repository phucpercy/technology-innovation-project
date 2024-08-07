# Technology Innovation Project
Welcome to the Technology Innovation Project! This repository showcases a project developed using the AWS Cloud Development Kit (CDK) with Python, focusing on building and deploying a web canary and web crawler, setting up monitoring and alerting, and creating a CI/CD pipeline.

## Project Overview
This project demonstrates the use of AWS CDK to define and deploy cloud infrastructure using Python. It includes multiple stages, each building on the previous one to extend the functionality and robustness of the deployed solution.

## Project Architecture
![alt text](https://github.com/phucpercy/technology-innovation-project/blob/main/images/Architecture.png?raw=true "Logo Title Text 1")
## Prerequisites
- Python 3.6 or later
- AWS CDK

## Getting Started
### Setting Up the Virtual Environment
```sh
python3 -m venv .venv
source .venv/bin/activate
```

### Installing Dependencies
```sh
pip install -r requirements.txt
```
### Synthesizing the CloudFormation Template
```sh
cdk synth
```

### Deploy shared stack for stages
```sh
cdk deploy CanarySharedStack
```

### Deploy system
```sh
cdk deploy CanaryPipelineStack
```

## Project Components
### Component 1: Canary Monitoring Application
- Functionalities: Monitoring Lambda function is triggered periodically by EventBridge rules to monitoing a list of URLs, which is stored in the DynamoDB and managed by another Lambda function. If pre-defined threshold for each URL is crossed, SNS will trigger a Lambda to email to users by SES and store the details in DynamoDB.
- Key Components: Lambda, DynamoDB, SNS, SES, Cloudwatch, EventBridge

### Component 2: Extending the Canary into a Web Crawler
- Functionalities: Extend the canary to crawl a custom list of websites stored in an S3 bucket.
- Key Components: AWS Monitoring and Notification services

### Component 3: Creating a Multi-Stage CI/CD Pipeline
Objective: Create a CI/CD pipeline with Beta/Gamma and Prod stages using AWS CDK, including bake times, code reviews, and test blockers.
Key Components: AWS CodePipeline, CodeDeploy, PyTest

Stage 5: Building a CRUD API for the Web Crawler
Objective: Build a public CRUD API Gateway endpoint for managing the list of websites to crawl, using DynamoDB.
Key Components: API Gateway, DynamoDB
Learning Objectives:
Creating RESTful API interfaces
Implementing business logic with Python
Extending CI/CD pipelines to include CRUD operations and DynamoDB performance tests
Useful Commands
cdk ls: List all stacks in the app
cdk synth: Emit the synthesized CloudFormation template
cdk deploy: Deploy the stack to your default AWS account/region
cdk diff: Compare deployed stack with current state
cdk docs: Open CDK documentation
Project Structure
app.py: Main entry point for the CDK application
config.py: Configuration file for the project
requirements.txt: List of required Python packages
requirements-dev.txt: List of development dependencies
tests/: Directory containing unit tests
.gitignore: Git ignore file


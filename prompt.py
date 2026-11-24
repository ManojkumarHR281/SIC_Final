# # PROJECT UPGRADE: Transform Evidence-Calibrated Code Review into a Genuine Machine Learning and NLP-Based Intelligent Code Review System

# ## 1. Project Objective

# I have an existing project named **Evidence-Calibrated Code Review**.

# I want you to transform the existing application into a genuine Machine Learning (ML) and Natural Language Processing (NLP) based code review system.

# The current application primarily uses:
# - Python AST parsing
# - Manually defined security rules
# - Static code analysis
# - Heuristic-based confidence calculations
# - Heuristic-based uncertainty calculations

# I do NOT want the final application to depend primarily on manually written rules or keyword matching.

# I want actual machine learning models trained and evaluated on real, publicly available datasets.

# The final application should use:
# 1. Machine Learning for code vulnerability detection and defect classification.
# 2. NLP for understanding vulnerability descriptions, explaining findings, and generating remediation guidance.
# 3. Statistical probability calibration for reliable confidence estimates.
# 4. Evidence-based reasoning to explain why the model generated a prediction.

# **Important:** Do not simply create mock ML functionality. Implement real dataset loading, preprocessing, training, evaluation, model saving, model loading, and inference.

# ---

# ## 2. Preserve the Existing Application

# Before modifying anything:

# 1. Inspect the complete existing repository.
# 2. Understand its Flask architecture.
# 3. Identify existing routes, templates, database models, services, utilities, and tests.
# 4. Understand how the current review pipeline works.
# 5. Identify which modules should be replaced, extended, or preserved.

# Existing technologies:
# - Python
# - Flask
# - Flask-SQLAlchemy
# - SQLite
# - HTML
# - CSS
# - JavaScript
# - Bootstrap
# - Chart.js

# Preserve the existing:
# - Dashboard
# - Review submission interface
# - Review history
# - Reports
# - Analytics
# - Settings
# - API endpoints
# - Database functionality

# Do not rebuild the entire application from scratch.

# Integrate the ML and NLP components into the existing architecture.

# ---

# ## 3. Machine Learning Implementation

# ### A. Main ML objective

# Develop a machine learning model that predicts whether a submitted code snippet contains a potential vulnerability or software defect.

# The model should learn patterns from labeled training data instead of depending on manually written vulnerability rules.

# Implement these prediction categories:

# - Vulnerable
# - Non-vulnerable
# - Uncertain / insufficient evidence

# Where the dataset supports it, also classify vulnerability categories such as:

# - SQL Injection
# - Command Injection
# - Buffer Overflow
# - Cross-Site Scripting
# - Path Traversal
# - Improper Input Validation
# - Insecure Deserialization
# - Authentication and Authorization Issues

# Do not claim that every category is supported unless the training data contains sufficient labeled examples.

# ### B. Dataset integration

# Use genuine, publicly available datasets.

# Investigate and select appropriate datasets from the following sources:

# 1. Devign Dataset:
# https://github.com/secureIT-project/Devign

# 2. Big-Vul Dataset:
# https://github.com/ZeoVan/MSR_20_Code_vulnerability_CSV_Dataset

# 3. CodeXGLUE:
# https://github.com/microsoft/CodeXGLUE

# 4. Juliet Test Suite:
# https://samate.nist.gov/SARD/test-suites/

# 5. NVD Vulnerability Database:
# https://nvd.nist.gov/

# Dataset requirements:

# - Download or obtain the actual datasets.
# - Document their licenses and sources.
# - Identify their programming languages.
# - Identify their labels and class distributions.
# - Remove duplicate and invalid samples.
# - Handle missing values.
# - Normalize labels.
# - Remove corrupted or unusable code samples.
# - Preserve the original dataset attribution.

# IMPORTANT:
# Do not mix incompatible programming languages or assume that C/C++ vulnerability datasets are Python datasets.

# Start with the best-supported language and make the supported language limitations explicit.

# If Python-specific labeled training data is insufficient, investigate an appropriate additional dataset rather than pretending that another language's samples are Python.

# Use the datasets to create a reproducible training pipeline.

# ### C. ML model architecture

# Implement a real code classification model.

# Preferred model:

# **CodeBERT**

# Hugging Face:
# https://huggingface.co/microsoft/codebert-base

# Alternative:
# - TF-IDF + Logistic Regression as a baseline.
# - Random Forest as a baseline.
# - CodeBERT fine-tuning for the primary deep-learning model.

# Use:
# - PyTorch
# - Hugging Face Transformers
# - Hugging Face Datasets
# - Scikit-learn
# - Pandas
# - NumPy

# The system should include:

# 1. Dataset loader.
# 2. Data preprocessing.
# 3. Tokenization.
# 4. Train-validation-test splitting.
# 5. Model training.
# 6. Validation.
# 7. Hyperparameter configuration.
# 8. Model evaluation.
# 9. Model checkpoint saving.
# 10. Model loading for inference.

# Use a reproducible random seed.

# Avoid data leakage by splitting at the project or repository level wherever possible. Do not allow duplicate or near-duplicate code samples to appear across training and test sets.

# Handle class imbalance using appropriate techniques such as class weights or carefully selected sampling.

# ### D. Model outputs

# For every submitted code sample, produce:

# - Predicted class.
# - Predicted vulnerability category, where supported.
# - Model probability.
# - Confidence score.
# - Uncertainty score.
# - Model version.
# - Relevant code location, when available.

# Do not interpret an uncalibrated softmax output as a statistically reliable probability.

# ---

# ## 4. NLP Implementation

# I want a genuine NLP component, not just predefined explanations.

# ### A. NLP objectives

# Implement NLP functionality for:

# 1. Understanding vulnerability descriptions.
# 2. Classifying vulnerability descriptions.
# 3. Mapping natural-language vulnerability descriptions to CWE categories.
# 4. Generating understandable explanations of detected vulnerabilities.
# 5. Generating remediation suggestions.
# 6. Summarizing code review reports.

# ### B. NLP datasets

# Use actual public text datasets and documentation.

# Potential sources:

# - NVD CVE vulnerability descriptions:
#   https://nvd.nist.gov/developers/vulnerabilities

# - MITRE CWE database:
#   https://cwe.mitre.org/

# - CodeXGLUE:
#   https://github.com/microsoft/CodeXGLUE

# Download, preprocess, and document the selected data.

# Use NVD vulnerability descriptions and CWE labels for a supervised vulnerability-description classification task.

# Do not treat the CWE descriptions themselves as labeled training examples without constructing valid input-label pairs.

# ### C. NLP models

# Use Hugging Face transformer models.

# Suggested models:

# - DistilBERT for vulnerability-description classification.
# - BERT for text classification.
# - CodeBERT for code-related representations.
# - T5 or FLAN-T5 for natural-language explanations, if a suitable training or grounded inference approach is implemented.

# Implement at least one trained NLP model.

# The NLP system should understand a description such as:

# "User-controlled input is passed into an SQL query without proper parameterization."

# It should identify relevant security concepts and predict the appropriate CWE category when supported by its training labels.

# ### D. Explanation generation

# After the ML model identifies a potential vulnerability, the NLP component should generate an explanation.

# Example:

# Input code:

# ```python
# query = "SELECT * FROM users WHERE id = " + user_id
# cursor.execute(query)
# ```

# Expected explanation:

# "The application constructs an SQL query by concatenating a variable into the query string. If the variable is controlled by an external user, this may allow SQL injection."

# Expected remediation:

# "Use parameterized queries instead of directly concatenating user-controlled values."

# The explanation must be grounded in the submitted code and model findings.

# Never invent line numbers, evidence, or vulnerabilities.

# If an LLM API is used, make it optional and clearly distinguish its output from the trained NLP model's output.

# ---

# ## 5. Replace Rule-Based Confidence with ML-Based Confidence Calibration

# The existing confidence calculator uses manually assigned weights.

# I want a statistically grounded alternative.

# Implement probability calibration using:

# - Platt Scaling
# - Isotonic Regression
# - Temperature Scaling

# Compare calibration performance and choose the most appropriate approach using validation data.

# Evaluate with:

# - Brier Score
# - Expected Calibration Error (ECE)
# - Reliability Diagrams
# - Precision
# - Recall
# - F1 Score
# - ROC-AUC
# - PR-AUC

# The final result should distinguish:

# 1. Model prediction probability.
# 2. Calibrated probability.
# 3. Predictive uncertainty.
# 4. Evidence completeness.

# Use a suitable uncertainty estimation method, such as:

# - Predictive entropy.
# - Monte Carlo dropout.
# - Ensemble disagreement.

# Do not use the simple formula 1 - confidence as the only uncertainty method.

# If the model has insufficient evidence or encounters out-of-distribution input, clearly communicate that limitation.

# ---

# ## 6. Hybrid Analysis Architecture

# The primary vulnerability prediction must come from trained ML models.

# The NLP model should support text classification and explanations.

# AST can still be used for:
# - Extracting code structure.
# - Locating functions and code statements.
# - Mapping predictions to line numbers.
# - Supporting explainability.

# However, AST rules and manually written security patterns must not be the primary vulnerability classification mechanism.

# Implement the following architecture:

# User submits source code
#         |
#         v
# Flask application
#         |
#         v
# Code preprocessing
#         |
#         +--------------------------+
#         |                          |
#         v                          v
#    CodeBERT model             AST extraction
#         |                          |
#         v                          v
#  ML vulnerability prediction  Code location/context
#         |                          |
#         +------------+-------------+
#                      |
#                      v
#             Prediction evidence
#                      |
#                      v
#           Probability calibration
#                      |
#                      v
#              Uncertainty engine
#                      |
#                      v
#              NLP explanation
#                      |
#                      v
#             Final review report

# The system should work locally after models and datasets have been downloaded.

# ---

# ## 7. Frontend Improvements

# Preserve the current frontend while upgrading it to show real ML and NLP results.

# Add the following sections.

# ### A. ML Analysis Dashboard

# Display:
# - Selected ML model.
# - Model version.
# - Prediction category.
# - Vulnerability probability.
# - Calibrated confidence.
# - Uncertainty.
# - Number of code samples analyzed.
# - Model evaluation metrics.

# ### B. NLP Explanation Panel

# Display:
# - Detected vulnerability description.
# - CWE category.
# - Explanation in understandable language.
# - Potential impact.
# - Suggested remediation.
# - Explanation confidence or provenance.

# ### C. Model Performance Dashboard

# Display actual evaluation metrics:

# - Accuracy.
# - Precision.
# - Recall.
# - F1 Score.
# - ROC-AUC.
# - PR-AUC.
# - Brier Score.
# - Calibration error.

# Use Chart.js to display:
# - Training and validation loss.
# - Confusion matrix.
# - Class distribution.
# - Precision and recall.
# - Calibration curves.

# Never use hardcoded or fabricated metrics.

# If a model has not been trained, show "Model not trained" rather than displaying fake results.

# ### D. Prediction Results

# For each finding show:

# - File name.
# - Line number, when available.
# - Vulnerability category.
# - Predicted class.
# - Calibrated probability.
# - Uncertainty level.
# - NLP-generated explanation.
# - Remediation suggestion.
# - Model provenance.

# ---

# ## 8. Backend Architecture

# Create a modular ML/NLP architecture.

# Suggested directory structure:

# ```text
# app/
#     ml/
#         dataset_loader.py
#         preprocessing.py
#         code_tokenizer.py
#         train_code_model.py
#         code_classifier.py
#         model_registry.py
#         evaluation.py
#         calibration.py
#         uncertainty.py

#     nlp/
#         nlp_preprocessing.py
#         vulnerability_classifier.py
#         explanation_generator.py
#         cwe_mapper.py
#         report_summarizer.py

#     services/
#         review_engine.py
#         evidence_engine.py
#         ml_review_service.py
#         nlp_service.py

#     routes/
#         review.py
#         dashboard.py
#         analytics.py

#     models/
#         review_model.py
#         prediction_model.py

# datasets/
#     raw/
#     processed/

# trained_models/
#     codebert/
#     nlp_classifier/
#     calibration/

# training/
#     train.py
#     evaluate.py
#     prepare_dataset.py

# tests/
#     test_dataset.py
#     test_ml_model.py
#     test_nlp.py
#     test_calibration.py
#     test_integration.py
# ```

# Adapt this structure to the existing repository rather than creating duplicate modules unnecessarily.

# ---

# ## 9. API Integration

# Integrate the new functionality into the existing Flask APIs.

# Create or extend endpoints for:

# - Code vulnerability prediction.
# - NLP vulnerability-description classification.
# - Explanation generation.
# - Model information.
# - Model evaluation metrics.
# - Model training status.

# Example API response:

# ```json
# {
#   "prediction": "vulnerable",
#   "vulnerability_type": "SQL Injection",
#   "cwe": "CWE-89",
#   "model": "CodeBERT",
#   "model_probability": 0.91,
#   "calibrated_probability": 0.87,
#   "uncertainty": 0.12,
#   "explanation": "User-controlled input may be inserted into an SQL query.",
#   "recommendation": "Use parameterized SQL queries."
# }
# ```

# This is an illustrative response format, not a result to hardcode.

# ---

# ## 10. Privacy and Security

# Maintain the local-first approach.

# Requirements:

# - Never execute submitted source code.
# - Never execute downloaded training samples.
# - Process untrusted source code as data.
# - Avoid sending source code to external APIs by default.
# - Keep model inference local where possible.
# - Document dataset licensing and attribution.
# - Provide a way to delete stored review information.
# - Avoid storing complete submitted source code unless explicitly required and consented to.

# ---

# ## 11. Testing and Validation

# Implement tests for:

# - Dataset loading.
# - Data cleaning.
# - Tokenization.
# - Model training.
# - Model inference.
# - NLP classification.
# - Explanation generation.
# - Probability calibration.
# - Uncertainty estimation.
# - Flask integration.
# - Existing functionality.

# Test with previously unseen code samples.

# Compare the ML model against the baseline model.

# Provide a final evaluation report showing actual measured results.

# Do not claim success merely because the training script runs.

# ---

# ## 12. Performance and Hardware

# The project should support:

# - GPU training when CUDA is available.
# - CPU inference for systems without GPUs.
# - Configurable batch sizes.
# - Configurable training epochs.
# - Model checkpointing.
# - Reproducible training.

# Do not require the entire dataset or model to be retrained every time the Flask application starts.

# Provide separate commands for dataset preparation, training, evaluation, and application startup.

# ---

# ## 13. Documentation

# Update README.md with:

# 1. Project overview.
# 2. New ML and NLP architecture.
# 3. Dataset sources and licenses.
# 4. Dataset preprocessing.
# 5. Training methodology.
# 6. Model architecture.
# 7. NLP methodology.
# 8. Evaluation metrics.
# 9. Installation instructions.
# 10. Model download instructions.
# 11. Training commands.
# 12. Application startup commands.
# 13. API documentation.
# 14. Limitations and supported languages.

# Include actual commands that work on Windows PowerShell.

# ---

# ## 14. Final Implementation Requirements

# Follow these requirements strictly:

# 1. Do not replace real ML with manually written rules.
# 2. Do not use random predictions.
# 3. Do not generate fake accuracy or training metrics.
# 4. Do not claim that a pretrained model was fine-tuned unless it actually was.
# 5. Do not claim NLP implementation merely because an LLM API is available.
# 6. Train at least one actual ML model using labeled datasets.
# 7. Train at least one actual NLP classification model using labeled text data.
# 8. Integrate both models into the existing Flask application.
# 9. Preserve all existing working features.
# 10. Make the application runnable in VS Code on Windows.
# 11. Add proper error handling when datasets or model checkpoints are unavailable.
# 12. Document every model and dataset used.

# ### Final deliverables

# I expect:

# - A fully upgraded source-code repository.
# - Dataset preparation scripts.
# - ML training scripts.
# - NLP training scripts.
# - Trained model checkpoints or reproducible instructions to obtain them.
# - Model evaluation reports.
# - Integrated Flask application.
# - Updated frontend.
# - Automated tests.
# - Updated README.
# - Complete Windows installation and execution instructions.

# ### Most important instruction

# Do not stop after creating the architecture or empty ML/NLP modules.

# Actually implement the dataset pipelines, train the models where computational resources permit, evaluate them, integrate inference into the application, and verify that the application works.

# If a dataset or model cannot be downloaded or trained in the available environment, explain exactly what is missing and provide a reproducible command to complete that step. Never substitute mock functionality.

# The final project must genuinely demonstrate Machine Learning, NLP, statistical confidence calibration, and evidence-based code review.
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>AI Powered IT Ticket Automation System – README</title>
    <style>
        body {
            font-family: Arial, Helvetica, sans-serif;
            line-height: 1.6;
            margin: 40px;
            background-color: #f9fafb;
            color: #1f2937;
        }
        h1, h2, h3 {
            color: #111827;
        }
        h1 {
            border-bottom: 3px solid #2563eb;
            padding-bottom: 10px;
        }
        h2 {
            border-bottom: 2px solid #e5e7eb;
            padding-bottom: 6px;
            margin-top: 32px;
        }
        code, pre {
            background: #111827;
            color: #f9fafb;
            padding: 12px;
            border-radius: 6px;
            display: block;
            overflow-x: auto;
        }
        ul {
            margin-left: 20px;
        }
        .section {
            margin-bottom: 30px;
        }
        .highlight {
            background: #eef2ff;
            padding: 12px;
            border-left: 5px solid #2563eb;
            margin: 16px 0;
        }
        footer {
            margin-top: 50px;
            text-align: center;
            font-size: 14px;
            color: #6b7280;
        }
    </style>
</head>

<body>

<h1>AI Powered IT Ticket Automation System</h1>

<p>
This project implements an intelligent IT support ticket automation platform using
<strong>Machine Learning, Natural Language Processing (NLP), Generative AI embeddings</strong>,
and <strong>ServiceNow integration</strong>. The system automates ticket classification,
priority prediction, routing, and lifecycle management.
</p>

<div class="highlight">
<strong>Academic Context:</strong><br>
BITS Pilani – ZC499T Capstone Project<br>
Semester 8 – Software Engineering
</div>

<hr>

<div class="section">
<h2>1. Project Overview</h2>

<p>
Modern IT support teams handle large volumes of tickets coming from web portals and emails.
Manual triaging is time-consuming, inconsistent, and error-prone.
This system addresses these challenges by using AI to:
</p>

<ul>
    <li>Automatically classify ticket category</li>
    <li>Predict ticket priority</li>
    <li>Assign resolver groups</li>
    <li>Integrate with ServiceNow for incident creation</li>
    <li>Track ticket status asynchronously using background workers</li>
</ul>
</div>

<div class="section">
<h2>2. Key Features</h2>

<ul>
    <li>AI-based ticket category & priority prediction</li>
    <li>Email-based and web-based ticket submission</li>
    <li>Sentence embedding using Hugging Face Transformers</li>
    <li>Django-based web application</li>
    <li>Admin & user dashboards</li>
    <li>ServiceNow REST API integration</li>
    <li>Asynchronous processing using Celery</li>
    <li>Retry & error handling with logging</li>
</ul>
</div>

<div class="section">
<h2>3. Technology Stack</h2>

<h3>Backend</h3>
<ul>
    <li>Python 3.11+</li>
    <li>Django</li>
    <li>Django ORM</li>
    <li>Celery + Redis</li>
</ul>

<h3>AI / ML</h3>
<ul>
    <li>SentenceTransformers</li>
    <li>Hugging Face Transformer Models</li>
</ul>

<h3>Frontend</h3>
<ul>
    <li>HTML, CSS</li>
    <li>Bootstrap 5</li>
    <li>Chart.js</li>
</ul>

<h3>Integrations</h3>
<ul>
    <li>ServiceNow REST APIs</li>
    <li>Email (SMTP / IMAP)</li>
</ul>
</div>

<div class="section">
<h2>4. System Architecture</h2>

<ul>
    <li>User submits ticket via Web or Email</li>
    <li>NLP preprocessing and embedding generation</li>
    <li>ML model predicts category and priority</li>
    <li>Ticket stored in Django database</li>
    <li>Celery task syncs ticket to ServiceNow</li>
    <li>Periodic Celery Beat updates ServiceNow status</li>
</ul>
</div>

<div class="section">
<h2>5. Machine Learning Design</h2>

<ul>
    <li>Sentence embeddings generated using Hugging Face MiniLM model</li>
    <li>Supervised classifier trained on labeled ticket data</li>
    <li>Confidence scores stored for category & priority</li>
    <li>Model is modular and extensible</li>
</ul>

<p>
<strong>Note:</strong> Hugging Face models are used for semantic embeddings, while
classification logic is trained using project-specific datasets.
</p>
</div>

<div class="section">
<h2>6. ServiceNow Integration</h2>

<ul>
    <li>Incident creation via REST API</li>
    <li>Assignment group mapping</li>
    <li>Priority, urgency, impact mapping</li>
    <li>Periodic status synchronization</li>
    <li>Error logging and retry mechanisms</li>
</ul>
</div>

<div class="section">
<h2>7. Background Processing</h2>

<ul>
    <li>Celery workers handle ServiceNow API calls</li>
    <li>Celery Beat schedules periodic jobs</li>
    <li>Retry policies for transient failures</li>
    <li>Supports horizontal scaling in production</li>
</ul>
</div>

<div class="section">
<h2>8. User Roles</h2>

<h3>Normal Users</h3>
<ul>
    <li>Submit tickets</li>
    <li>View ticket status</li>
    <li>Reset password</li>
    <li>Email verification</li>
</ul>

<h3>Admin Users</h3>
<ul>
    <li>Manage tickets</li>
    <li>Edit assignment groups</li>
    <li>View dashboards and analytics</li>
    <li>Override ticket details</li>
</ul>
</div>

<div class="section">
<h2>9. Security Features</h2>

<ul>
    <li>User authentication & authorization</li>
    <li>Email verification on registration</li>
    <li>Password reset & change flows</li>
    <li>CSRF protection</li>
</ul>
</div>

<div class="section">
<h2>10. Logging & Monitoring</h2>

<ul>
    <li>Centralized logging to file</li>
    <li>Error tracking for ServiceNow sync</li>
    <li>Retry counters and timestamps</li>
</ul>
</div>

<div class="section">
<h2>11. Setup & Installation</h2>

<pre>
1. Create virtual environment
2. Install dependencies from requirements.txt
3. Configure settings.py (DB, Email, ServiceNow, Redis)
4. Run migrations
5. Start Redis
6. Start Celery worker
7. Start Celery beat
8. Run Django server
</pre>
</div>

<div class="section">
<h2>12. Future Enhancements</h2>

<ul>
    <li>Self-learning model retraining</li>
    <li>Real-time email ingestion via Celery Beat</li>
    <li>Advanced GenAI-based summarization</li>
    <li>Multi-tenant support</li>
    <li>Production-grade monitoring (Prometheus/Grafana)</li>
</ul>
</div>

<div class="section">
<h2>13. Conclusion</h2>

<p>
This project demonstrates a complete, scalable, and industry-aligned approach to
automating IT ticket management using AI, ML, and modern backend technologies.
It is suitable for academic evaluation as well as real-world enterprise extensions.
</p>
</div>


</body>
</html>

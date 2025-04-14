# IMIS Google Scholar alert

Google Scholar email alert ingestion.

MongoDB should be running (see docker-compose)
RabbitMQ should be running (see docker-compose)

Connect to the container where the python app is running.
```
docker exec -it imis-google-scholar-alert-python-app-1 /bin/bash
```
Start the listener that parses the email body.
```
python -m app.src.main process-email-body
```
Start the listener that looks up the DOI from the search result.
```
python -m app.src.main process-search-doi
```
Start the listener that looks up Crossref for a given DOI.
```
python -m app.src.main process-crossref
```
Run the command that reads emails from the inbox and processes them.
```
python -m app.src.main process-unread-emails
```

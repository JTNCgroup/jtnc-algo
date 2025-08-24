FROM python:3.12-slim

WORKDIR /app

# install python modules
COPY requirements.txt .
RUN apt update && apt upgrade
RUN apt install sqlite3
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# copy all files to the working dir
# COPY . .

# expose port 8111 for accessing FastAPI
EXPOSE 8111

# run Uvicorn server on port 8111
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8111"]
# CMD ["tail", "-f", "/dev/null"]
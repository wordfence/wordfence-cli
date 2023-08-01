FROM python:3.11.4
WORKDIR /usr/src/app

# install any dependencies, libraries etc.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# copy application source code
COPY . .

# run the application, bringing in command line arguments
ENTRYPOINT [ "python", "./main.py" ]

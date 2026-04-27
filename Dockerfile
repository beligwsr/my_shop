FROM python:3.11
WORKDIR /my_shop
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "main.wsgi:application", "--bind", "0.0.0.0.:8000"]
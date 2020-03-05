EXPOSE 8080
CMD ["gunicorn", "--config", "main:app"]
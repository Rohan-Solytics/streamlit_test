from django.db import models

class SSLCertificate(models.Model):
    branch_name = models.CharField(max_length=100, unique=True)
    hostname = models.CharField(max_length=255)
    certificate = models.TextField()
    private_key = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"SSL for {self.hostname}"
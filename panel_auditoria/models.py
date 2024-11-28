# models.py
from django.db import models

class Cliente(models.Model):
    nombre = models.CharField(max_length=100)
    email = models.EmailField()
    # Otros campos necesarios para el cliente

    def __str__(self):
        return self.nombre

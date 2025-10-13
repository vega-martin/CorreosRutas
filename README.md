# Implementación de un sistema para la generación de paradas virtuales en envíos no registrados a partir de rutas históricas de reparto postal

El proyecto tiene como finalidad el desarrollo de un sistema que permita generar puntos de parada virtuales destinados a la gestión de envíos no registrados.
Para la identificación de estos puntos se emplearán los datos históricos de las rutas de los repartidores de la empresa postal, de forma que puedan localizarse lugares óptimos donde realizar dichas entregassin necesidad de añadir complejidad logística adicional.

Este proyecto consistirá en una aplicación web desacoplada que se dividirá en dos microservicios (frontenf y backend) conectados através de una API
---
## Microservicio 1: Frontend
Portal web que servirá como interfaz de acceso para los usuarios, ofreciendo un entorno sencillo y funcional desde el que interactuar con el servicio.

También contará con un módulo de visualización que permitirá mostrar los resultadosdel análisis de rutas y la ubicación del os puntos de parada virtuales sobre mpaas interactivos.

## Microservicio 2: Backend
Algoritmos de filtrado de datos, clustering y creación de paradas virtuales.

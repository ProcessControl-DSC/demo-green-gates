==============================
Tour Builder (Process Control)
==============================

**Autor:** Process Control | https://www.processcontrol.es

Landing de reserva de tours multi-parada: el visitante construye su ruta
sobre un mapa interactivo (una parada por noche, eligiendo tipo de plaza y
número de caballos) y envía el tour completo como un único presupuesto,
listo para el flujo de validación interna, firma online y señal del 50 %.

Funcionalidades
===============

* Página pública ``/tour`` con mapa (Leaflet/OpenStreetMap) y panel de itinerario.
* Cada parada con su fecha, noches, tipo de plaza (box/hierba) y nº de caballos.
* Precio estimado en tiempo real según las tarifas de alquiler del producto.
* El envío crea UN presupuesto con una línea por parada y programa una
  actividad de validación para el equipo de reservas.
* El presupuesto nace con firma online y pago requeridos: el flujo estándar
  de «Firmar & pagar» (señal del 50 %) continúa sin desarrollo adicional.

Configuración
=============

En la ficha de producto (pestaña Información general), marcar «Tour Stop» e
informar latitud, longitud y capacidad. Solo se publican en ``/tour`` los
productos publicados en el sitio web con coordenadas.

Uso
===

Abrir ``/tour``, pulsar un pin del mapa, «Añadir parada», ajustar fechas,
noches y caballos, rellenar los datos de contacto y enviar. El pedido
aparece en Ventas como presupuesto con la actividad «Validate web tour
request».

Datos técnicos
==============

**Modelos extendidos:**

* ``product.template`` — campos ``is_tour_stop``, ``tour_latitude``,
  ``tour_longitude``, ``tour_capacity`` y helper ``pc_tour_stop_data()``.
* ``sale.order`` — método ``pc_create_tour_order(customer, stops)``.

**Controladores:**

* ``GET /tour`` — landing pública.
* ``POST /tour/submit`` — creación del presupuesto (JSON).

Créditos
========

**Desarrollado por** `Process Control <https://www.processcontrol.es>`_

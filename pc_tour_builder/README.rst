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

Motor de ruta
=============

* El visitante indica ciudad de origen y destino (geocodificadas con
  Nominatim/OpenStreetMap) y elige el vehículo de transporte.
* El servidor calcula la ruta real por carretera con OSRM (gratuito, sin
  clave). Si en Ajustes se activa Google Maps y se informa la clave, usa la
  API Directions de Google. Si el motor externo falla, hay un fallback de
  línea recta (haversine) para que la landing nunca se rompa.
* La duración se estima con la velocidad media del vehículo configurado, no
  con la del proveedor, para respetar la configuración del cliente.
* Según las horas máximas de conducción por tramo del vehículo, el sistema
  trocea la ruta y sugiere la cuadra publicada más cercana a cada punto de
  descanso, sin repetir y solo si hay una a menos de 60 km.

Configuración
=============

**Transporte:** en Ventas → Tour Builder → Configuración de transporte,
definir los vehículos (velocidad media, horas máximas por tramo, descanso).
El módulo siembra «Camión grande» y «Furgoneta 2 caballos».

**Proveedor de rutas:** en Ajustes → Tour Builder, marcar «Usar Google Maps
para el cálculo de rutas» e informar la clave de API. Por defecto se usa OSRM
gratuito.


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

**Modelos:**

* ``product.template`` — campos ``is_tour_stop``, ``tour_latitude``,
  ``tour_longitude``, ``tour_capacity`` y helper ``pc_tour_stop_data()``.
* ``sale.order`` — método ``pc_create_tour_order(customer, stops)``.
* ``pc.transport.config`` — vehículos de transporte (velocidad media, horas
  máximas por tramo, descanso).
* ``pc.tour.router`` — motor de ruta (``compute_route``, ``suggest_stops``).
* ``res.config.settings`` — proveedor de rutas (OSRM/Google) y clave de API.

**Controladores:**

* ``GET /tour`` — landing pública.
* ``POST /tour/submit`` — creación del presupuesto (JSON).
* ``POST /tour/route`` — ruta por carretera ``{provider, distance_km,
  duration_h, geometry}``.
* ``POST /tour/suggest`` — cuadras intermedias sugeridas + ruta completa.

Créditos
========

**Desarrollado por** `Process Control <https://www.processcontrol.es>`_

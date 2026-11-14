<p align="center">
  <img src="../../.github/assets/hem-banner.svg" alt="Home Gerenciador de Medio Ambiente - Calidad del aire, comodidad, ventilación y control climático más inteligentes" width="1200">
</p>

<p align="center">
  <a href="https://ko-fi.com/chreece"><img src="../../.github/assets/ko-fi-banner.svg" alt="Apoyo a Grecia en Ko-fi" width="500"></a>
</p>



<a id="hem---home-environment-manager"></a>
<!-- HEM-LANGUAGE-SELECTOR-START -->
<p align="center">
  <a href="README.ar.md">العربية</a> · <a href="README.bg.md">Български</a> · <a href="README.bn.md">বাংলা</a> · <a href="README.cs.md">Čeština</a> · <a href="README.da.md">Dansk</a> · <a href="README.de.md">Deutsch</a> · <a href="README.el.md">Ελληνικά</a> · <a href="../../README.md">English</a> · <strong>Español</strong> · <a href="README.fa.md">فارسی</a> · <a href="README.fi.md">Suomi</a> · <a href="README.fr.md">Français</a> · <a href="README.he.md">עברית</a> · <a href="README.hi.md">हिन्दी</a> · <a href="README.hr.md">Hrvatski</a> · <a href="README.hu.md">Magyar</a> · <a href="README.id.md">Bahasa Indonesia</a> · <a href="README.it.md">Italiano</a> · <a href="README.ja.md">日本語</a> · <a href="README.ko.md">한국어</a> · <a href="README.nb.md">Norsk bokmål</a> · <a href="README.nl.md">Nederlands</a> · <a href="README.pl.md">Polski</a> · <a href="README.pt.md">Português</a> · <a href="README.pt-BR.md">Português (Brasil)</a> · <a href="README.ro.md">Română</a> · <a href="README.ru.md">Русский</a> · <a href="README.sk.md">Slovenčina</a> · <a href="README.sr.md">Српски</a> · <a href="README.sv.md">Svenska</a> · <a href="README.ta.md">தமிழ்</a> · <a href="README.th.md">ไทย</a> · <a href="README.tr.md">Türkçe</a> · <a href="README.uk.md">Українська</a> · <a href="README.ur.md">اردو</a> · <a href="README.vi.md">Tiếng Việt</a> · <a href="README.zh-Hans.md">简体中文</a> · <a href="README.zh-Hant.md">繁體中文</a>
</p>
<!-- HEM-LANGUAGE-SELECTOR-END -->

# HEM - Responsable del medio ambiente

<p align="center">
  <img src="../../.github/assets/hem-logo.svg" alt="HEM logotipo" width="420">
</p>

<p align="center"><strong>Todo el entorno de tu hogar, en una sola Home Assistant ¿Qué es eso?</strong></p>

**HEM ayuda a tu hogar a entender su entorno y reaccionar a lo que cada habitación realmente necesita.** Trae su Home Assistant los sensores, los datos meteorológicos, la información de ocupación y los dispositivos climáticos compatibles juntos para que pueda controlar la calidad del aire, recibir consejos útiles sobre ventilación, gestionar el confort y automatizar el equipo que elija.

Por ejemplo, HEM puede reducir la calefacción mientras todos están fuera, preparar habitaciones seleccionadas antes de regresar, usar un objetivo de humedad diferente mientras duerme, o pedirle que abra una ventana antes de ejecutar un deshumidificador. **control y recomendación**, sin controlar ningún dispositivo.

**Tú sigues a cargo.** Cada habitación tiene sus propias configuraciones, cada dispositivo con soporte tiene su propio controlador, modos de funcionamiento, objetivos y límites de seguridad. HEM nunca asume que la selección de un dispositivo le da permiso para operar ese dispositivo.

[Explora las características](#what-can-hem-do) · La Comisión [Ver la interfaz](#see-hem-in-action) · La Comisión [Instalar el HEM](#installation) · La Comisión [Establezca su hogar](#getting-started) · La Comisión [Guía detallada](../../docs/advanced-configuration.md)

<a id="what-can-hem-do"></a>
## ¿Qué puede HEM ¿Qué quieres decir?

| Su situación | ¿Cómo lo hizo? HEM puede ayudar |
| --- | --- |
| **La casa está vacía.** | Cambia a los objetivos Away, respeta las reglas de presencia de cada habitación y evita el uso innecesario de equipos seleccionados. |
| **Estás en camino a casa.** | Presiones **Prepárate para la llegada** para utilizar temporalmente los objetivos de comodidad en el hogar para los controladores automáticos elegibles, aunque todos estén todavía fuera. |
| **Alguien está durmiendo.** | Utilice objetivos de sueño, reduzca el ruido de los ventiladores o mantenga apagados los dispositivos seleccionados mientras cada habitación está durmiendo. |
| **Una habitación está húmeda.** | Comparar su indicación de humedad y moho con los objetivos, sugerir aire útil, o operar un deshumidificador autorizado utilizando PID el control. |
| **Está caliente y soleado.** | Evaluar la temperatura de la habitación, la luz solar, el clima y los contactos de ventanas conectados antes de mover los tonos optados. |
| **El aire al aire libre se ve mejor** | Se recomienda ventilación utilizando la demanda de interiores, la contaminación exterior, la temperatura, la humedad, el viento y los avisos de polen o clima disponibles. |
| **Un calentador o TRV deja de responder** | Muestre su estado de no disponibilidad o espera, mantenga su controlador configurado y informe fallas del dispositivo soportado sin suponer que se haya recuperado una batería o un relé. |

Estos son ejemplos, no acciones que HEM Los resultados dependerán de los sensores seleccionados, de la capacidad de cada dispositivo. Home Assistant las capacidades y sus configuraciones de acceso.

<a id="explore-the-features"></a>
## Explora las características

<a id="a-complete-home-dashboard"></a>
### Un panel de control completo para el hogar

El HEM la tarjeta le da una visión general útil sin abrir varias integraciones.

- Consulte las condiciones del exterior, la calidad del aire y si es recomendable ventilar.
- Comparar todas las habitaciones monitorizadas con un vistazo: temperatura, humedad relativa, AQI, PM2.5, indicación de moho, luz y otras lecturas de apoyo.
- Expande cualquier espacio para mediciones detalladas, información sobre ventanas y puertas, estado climático, controladores activos, razones de espera y estimaciones de física del edificio.
- Ver historias y tendencias, ver qué sensores contribuyeron a un promedio y distinguir las lecturas faltantes de los valores medidos.
- Habitaciones de grupo por número real Home Assistant los pisos, o utilizar una lista de habitaciones sencillas cuando no hay pisos.

<a id="different-settings-for-the-home-each-room-and-each-device"></a>
### Diferentes configuraciones para la casa, cada habitación y cada dispositivo

HEM mantiene las políticas compartidas separadas de las decisiones locales.

| Nivel de configuración | Lo que puede configurar |
| --- | --- |
| **En el hogar** | Fuentes de clima exterior y de contaminación, salas monitorizadas, límites globales de ventilación, presencia de los hogares, preparación de la llegada y entrega de anuncios. |
| **Habitación** | Fuentes de temperatura y humedad de interior, umbral de calidad del aire, contacto entre ventanas y puertas, comportamiento de sueño y ocupación, objetivos de comodidad específicos de la habitación, opciones de ventilación y sombreado. |
| **Dispositivo individual** | Sus modos de control disponibles, Automático/Manual/PID método, objetivos por perfil, sensores, configuración silenciosa del ventilador, tiempos mínimos de funcionamiento, protecciones de potencia, comportamiento de ventana y notificaciones de error del dispositivo. |

Los tres niveles son accesibles a través de configuraciones agrupadas y buscadas en la tarjeta. Los controles avanzados están disponibles cuando sea necesario, sin aglomerar las configuraciones cotidianas. Home Assistant cambios en la configuración.

<a id="climate-control-and-pid-device-by-device"></a>
### Control del clima y PID, dispositivo por dispositivo

HEM puede trabajar con compatible Home Assistant **el clima**, **humidificador** y **el ventilador** Dispositivos, incluidos equipos de calefacción, enfriamiento, deshumidificación, humidificación y apoyo para la circulación del aire o limpieza del aire.

Por cada uno **Modo de funcionamiento físico soportado**, elegir el método de control de forma independiente:

| Método | Lo que significa |
| --- | --- |
| **Las actuales** | Dejar de operar con la ruta del controlador existente. |
| **Automático** | Sigue HEMla demanda medida, los objetivos y permisos basados en la situación. |
| **PID** | Utilice el control proporcional, integral y derivado basado en retroalimentación cuando el dispositivo y la medición lo apoyen. |
| **Manual** | Control a través de solicitudes y objetivos explícitamente respaldados. |
| **Desactivado** | Mantenga ese controlador apagado, sujeto a los requisitos de protección física y retroalimentación. |

Por ejemplo, un aire acondicionado puede utilizar **PID para calefacción** y **Automático para enfriamiento**Un deshumidificador puede tener su propio PID Los aficionados elegibles pueden utilizar el sistema de calibración, los objetivos y el tiempo de ciclo. PID cuando estén disponibles retroalimentaciones adecuadas y controles específicos.

PID es **No** una supervisión universal: HEM Las opciones avanzadas incluyen ajuste y calibración por modo, ajustes sugeridos/adaptivos, operación silenciosa y ajustes de ventilador en etapa compatibles. Usted aprueba los cambios sugeridos a menos que opte explícitamente por una adaptación automática limitada.

<a id="comfortable-when-youre-home-economical-when-youre-away"></a>
### Comodo cuando estás en casa, económico cuando no estás

HEM puede elegir entre **Comodidad, hogar, lejos, sueño y ecología** objetivos basados en la situación del hogar, la evidencia de la habitación y sus selecciones explícitas.

- **En casa y fuera:** Utilice diferentes objetivos de calefacción, enfriamiento y humedad dependiendo de la presencia verificada en el hogar.
- **Presencia de la habitación:** Utilice un dispositivo elegible siempre que haya demanda, solo mientras su habitación esté ocupada o solo mientras la habitación esté vacía.
- **Dormir:** Aplicar objetivos nocturnos y comportamiento más silencioso del ventilador.
- **Eco:** Usar objetivos económicos cuando se configuren. Una puerta interior cerrada puede participar en una política ecológica protegida cuando se verifica que la habitación está vacía y se cumplen otras condiciones; una puerta cerrada por sí sola no prueba que la habitación está aislada.
- **Preparación para el despertar:** Utilice una fuente de alarma siguiente configurada para dejar el sueño automático antes de la alarma y dar tiempo a los dispositivos elegibles para responder.

Si la ocupación, la disponibilidad del dispositivo u otra evidencia requerida es incierta, HEM no simplemente asume que es seguro arrancar un dispositivo automático.

<a id="prepare-your-environment-before-you-arrive"></a>
### Prepare su entorno antes de llegar

**Prepárate para la llegada** Es una acción cronometrada para un hogar confirmado. HEMEs el dispositivo de casa.

HEM se aplica temporalmente la configuración **Objetivos para el hogar** a los automáticos elegibles/PID los controladores para que las habitaciones puedan comenzar a calentarse, enfriarse o ajustar la humedad antes de regresar. **sólo cuando ya tenga el permiso necesario de control físico**.

La preparación no es un comando para activar todo. Los dispositivos todavía necesitan una demanda genuina, sensores válidos y autorización, y deben respetar las ventanas, tiempos mínimos de encendido y apagado y sus propias protecciones. La acción termina cuando alguien llega, lo cancelas o el temporizador configurado expira. Home Assistant reiniciar no reinicia el tiempo completo.

<a id="ventilation-advice-windows-doors-and-shading"></a>
### Consejos de ventilación, ventanas, puertas y sombras

HEM comparaciones **¿Qué necesita una habitación?** con **si el aire exterior puede ayudar**.

- Recomienda abrir o cerrar ventanas utilizando las mediciones actuales de los interiores, la humedad exterior, la contaminación, la temperatura, el viento, las alertas meteorológicas y el contexto opcional del polen.
- Utilice los contactos de ventanas y puertas seleccionados para explicar las condiciones de la habitación y evite tratar a un contacto desconocido como cerrado.
- Opcionalmente, le pedirá que intente abrir una ventana antes de iniciar un aparato automático compatible, y luego continuar con el control normal después de que la respuesta configurada espere si es necesario.
- Utilice la información de la puerta para el conocimiento de los límites de la habitación, las precauciones de ventilación y el comportamiento ecológico opcional.
- Gestionar los persianas, persianas y sombras seleccionados utilizando las ventanas, temperatura, clima, elevación solar y pruebas de iluminación opcionales adecuadas.

HEM No se abre una ventana por sí sola porque la aireación ayudaría.

<a id="humidity-mold-indication-and-air-quality"></a>
### Humedad, indicación de moho y calidad del aire

HEM combina lecturas apoyadas como **temperatura, humedad, CO2, partículas, COV, IQI y iluminación** Las mediciones disponibles dependen de lo que su Home Assistant la configuración proporciona.

Su **indicación del molde** Estimar las condiciones de humedad en una superficie fría a partir de las temperaturas de la habitación y del exterior y una medición de calibración.

**La indicación de moho es una estimación, no un detector de moho o esporas.** Los datos de los sensores que faltan o están obsoletos no pueden justificar un nuevo comando de dispositivo basado en molde.

<a id="announcements-diagnostics-and-protection"></a>
### Anuncios, diagnóstico y protección

Puede enviar recomendaciones y alertas relevantes a través de configuraciones Home Assistant notificaciones, reproductores de medios de comunicación TTS o **El centro de anuncios**, con la redacción opcional de IA. IA puede cambiar la forma en que se expresa un mensaje; HEMLas decisiones de control físico siguen siendo deterministas.

HEM Incluye también protecciones y diagnósticos específicos del dispositivo:

- Duración mínima de encendido y apagado, ajustes máximos de tiempo de funcionamiento y manejo de interruptores de alimentación externos compatibles.
- Restricciones de ventana y ocupación, manejo manual y controles de reconocimiento de comandos nativos.
- Informe de error y dispositivo no disponible, con una opción de comportamiento de notificación para cada dispositivo.
- Un perro de vigilancia opcional después del cierre para la presunta continuación del calentamiento después de un comando de apagado, con vigilancia vigilada y tentativas limitadas de recuperación.
- Razones claras de espera, estado actual de funcionamiento y disponibilidad de la fuente, para que puedas investigar antes de habilitar más control.

**Los límites de seguridad siguen vigentes incluso cuando se deshabilita la alerta.** HEM nunca trata un envío de comando exitoso como prueba de que un aparato haya respondido físicamente.

<a id="see-hem-in-action"></a>
## ¿Ves ? HEM en acción

Estas ilustraciones en inglés usan muestras de habitaciones y mediciones, mostrando la interfaz en lugar de mostrar datos en vivo de una casa en particular.

<a id="home-at-a-glance"></a>
### A la casa en un vistazo

Obtenga consejos de ventilación, condiciones climáticas y el estado de cada habitación vigilada en una sola tarjeta.

<p align="center">
  <img src="../../docs/images/hem-dashboard-overview.svg" alt="HEM tablero de control en casa con asesoramiento de ventilación y lecturas ambientales en cinco habitaciones" width="900">
</p>

<a id="expand-a-room-for-full-details"></a>
### Ampliar una habitación para los detalles completos

Inspeccionar la calidad del aire, la indicación del moho, la presencia, el estado de las ventanas, los controladores climáticos y las explicaciones para cada decisión.

<p align="center">
  <img src="../../docs/images/hem-room-expanded.svg" alt="Tablero de mando ampliado de baño con lecturas y controladores independientes de dispositivos" width="760">
</p>

<a id="home-settings"></a>
### Configuración del hogar

Gestionar las fuentes al aire libre, la presencia en toda la casa, las habitaciones controladas, los límites de ventilación, la preparación y las notificaciones.

<p align="center">
  <img src="../../docs/images/hem-home-settings.svg" alt="HEM Configuraciones de hogar con grupos de búsqueda y gestión de fuentes y habitaciones" width="900">
</p>

<a id="room-settings"></a>
### Configuración de la habitación

Elige lo que importa para cada habitación: sus propios sensores, objetivos, ocupación, puertas, ventanas, ventilación, sombreado y salvaguardias.

<p align="center">
  <img src="../../docs/images/hem-room-settings.svg" alt="Grupos HEM configuración de la habitación para sensores, controles de dispositivos, sueño, ventanas y protección" width="760">
</p>

<a id="device-settings"></a>
### Configuración del dispositivo

Ajuste a la perfección un dispositivo sin cambiar los demás, incluidos los métodos de control compatibles, PID, la operación silenciosa, el tiempo y la denuncia de fallas.

<p align="center">
  <img src="../../docs/images/hem-device-settings.svg" alt="Grupos HEM configuración del dispositivo con control, PID, protección energética y notificaciones" width="900">
</p>

<a id="getting-started"></a>
## Comenzando

1. **Organicen sus habitaciones.** En el Home Assistant, crear o comprobar sus Áreas y asignar los sensores y dispositivos apropiados a cada uno.
2. **Elige qué controlar.** Añadir HEM, seleccione las habitaciones que le interesan y revise la temperatura, humedad, ventana, calidad del aire y las fuentes de dispositivo sugeridas.
3. **Configurar la información compartida.** Seleccione las fuentes disponibles de clima al aire libre/con calidad del aire, la evidencia de ocupación del hogar y los destinos de anuncios que desee.
4. **Agregue la tarjeta.** Abre un panel en modo de edición y agrega el **Gestión del medio ambiente del hogar** Comience con el seguimiento de la habitación, lecturas y consejos de ventilación.
5. **Habilitar el control sólo cuando sea útil.** Abre una habitación, elige un aparato soportado, revisa su controlador y seleccione explícitamente Automático o PID para los modos que quieras HEM para operar.

Lo haces. **No** Comience con los sensores que tiene, e introduzca el control automático un dispositivo a la vez.

<a id="add-the-card-manually"></a>
### Añadir la tarjeta manualmente

La integración normalmente registra su propia tarjeta Lovelace.

~~~yaml
type: custom:home-environment-manager-card
~~~

Si su Home Assistant la instalación tiene más de una HEM el sensor de recomendación, es posible que deba configurar el sensor de recomendación adecuado **entidad** de forma explícita:

~~~yaml
type: custom:home-environment-manager-card
entity: sensor.your_hem_recommendation_sensor
~~~

Para obtener instrucciones paso a paso sobre las fuentes de la habitación, los perfiles, PID las configuraciones, políticas de ventanas, preparación, calibración de moldes, sombreado solar y entrega de anuncios, utilizar la [Guía detallada de configuración](../../docs/advanced-configuration.md).

<a id="installation"></a>
## Instalación

<a id="hacs--home-assistant-community-store"></a>
### HACS / Home Assistant Tienda comunitaria

1. Abierto **HACS** en el Home Assistant.
2. Añadir **La Comisión Europea ha aprobado la Decisión de la Comisión de 13 de diciembre de 2011 sobre la aplicación de la Directiva 2009/138/CE del Parlamento Europeo y del Consejo.** como un **repositorio personalizado** en el **Integración** categoría si no está ya incluida en la lista.
3. Encuentra **Gestión del medio ambiente del hogar** y instalarlo.
4. Reinicio **Home Assistant** para cargar la integración.
5. ¡Vete a **Configuraciones → Dispositivos y servicios → Agregar integración**, la búsqueda de **Gestión del medio ambiente del hogar** y completar la configuración.

<a id="manual-installation"></a>
### Instalación manual

Copia del repositorio **personal_components/environment_manager** carpeta en la coincidencia **personalizado_componentes** directorio en su Home Assistant configuración, manteniendo el nombre del directorio **medio ambiente_manager**- Reiniciar . Home Assistant y añadir la integración a través de **Configuración → Dispositivos y servicios**.

Para cambios posteriores en la instalación, mantenga sus HEM Introducción y configuración de integración. recargar el panel de control en su navegador si la apariencia de la tarjeta no se actualiza inmediatamente.

<a id="common-questions"></a>
## Preguntas comunes

**¿Puedo usarlo? HEM ¿sin darle el control de mis dispositivos?**

Sí. El monitoreo, las mediciones, los consejos de ventilación, el historial y muchas indicaciones ambientales funcionan sin habilitar la activación del dispositivo.

**- ¿Qué quieres ? HEM ¿controlar automáticamente cada dispositivo que descubre?**

No. Selecciona los dispositivos físicos que desea administrar y selecciona explícitamente el método de control para los modos soportados.

**Todos los aparatos soportan PID?**

- No, no es así. HEM apoyo PID para **subvencionables** trayectorias de calefacción, enfriamiento, humedad o control de ventiladores cuando el aparato y las mediciones seleccionadas proporcionen las capacidades y retroalimentación necesarias. PID el control.

**¿Puedo darle reglas diferentes a cada habitación?**

Las condiciones de ocupación, el comportamiento del sueño, las fuentes, los objetivos y algunas preferencias de seguridad pueden variar según la habitación, mientras que cada dispositivo físico tiene sus propias configuraciones de funcionamiento y protección.

**Puede HEM ¿Preparar mi casa mientras estoy fuera?**

- Sí, es cierto. **Prepárate para la llegada** Los controladores automáticos elegibles y ya autorizados pueden utilizar los objetivos en el hogar durante un período limitado.

**¿Me abre las ventanas una recomendación de "bueno para la ventilación"?**

El movimiento automático es una característica separada y opt-in para los tonos o cubiertas compatibles, sujetos a sus propios controles de seguridad.

**¿Qué pasa si un sensor o un dispositivo no está disponible?**

HEM El control automático requiere una autoridad y pruebas válidas actuales.

<a id="help-and-troubleshooting"></a>
## Ayuda y solución de problemas

Si parece que algo está mal, revise la habitación o el controlador correspondiente **Razón**, **Diagnostica**, la disponibilidad de la fuente y el método de control actual. [Guía detallada de configuración](../../docs/advanced-configuration.md) cubre los estados de espera comunes, las políticas de presencia, PID Eligibilidad, ventanas y resolución de problemas de respuesta del dispositivo.

Para un problema reproducible, [abrir una GitHub La cuestión](https://github.com/Chreece/HA-Home-Environment-Manager/issues) con el comportamiento esperado, el comportamiento real, las configuraciones de habitación/dispositivo pertinentes y los pasos para reproducirse. Eliminar información privada de los registros e imágenes.

Las contribuciones y mejoras son bienvenidas. [Contribución.md](../../CONTRIBUTING.md).

<a id="support-and-license"></a>
## Apoyo y licencia

Si HEM es útil para usted, usted puede [apoyo a Grecia en Ko-fi](https://ko-fi.com/chreece).

Distribuido bajo el [Licencia del MIT](../../LICENSE).

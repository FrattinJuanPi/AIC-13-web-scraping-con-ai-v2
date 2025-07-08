# WebScraping AI Chatbot

Este proyecto implementa un chatbot inteligente que integra modelos de lenguaje avanzados (como Anthropic Claude) con herramientas de scraping y procesamiento de datos a través del protocolo MCP. El chatbot puede conectarse a múltiples servidores MCP, descubrir y utilizar herramientas disponibles en cada uno, y responder consultas del usuario de manera interactiva, llamando a herramientas externas cuando es necesario.

## Características principales

- **Integración con modelos de lenguaje:** Utiliza la API de Anthropic para generar respuestas y decidir cuándo invocar herramientas externas.
- **Conexión a múltiples servidores MCP:** Permite descubrir y utilizar herramientas de scraping y procesamiento de datos de diferentes servidores.
- **Interfaz interactiva:** El usuario puede realizar consultas en lenguaje natural y el chatbot gestionará la interacción con las herramientas necesarias.
- **Gestión de recursos asíncrona:** Uso de `AsyncExitStack` para una gestión eficiente y segura de las conexiones y recursos.

## Requisitos

- Python 3.8+
- Ver archivo `requirements.txt` para dependencias adicionales.

## Configuración

1. Crea un archivo `.env` en la raíz del proyecto y agrega tu API key de Anthropic:
2. Configura los servidores MCP en el archivo `server_config.json`.

## Uso

Ejecuta el chatbot con:

```
uv run mcp_chatbot.py
```

Sigue las instrucciones en pantalla para interactuar con el chatbot.
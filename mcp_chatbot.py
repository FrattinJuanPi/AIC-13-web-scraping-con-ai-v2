# Importa las librerías necesarias para manejo de variables de entorno, API de Anthropic, MCP, tipado, manejo de contexto asíncrono, JSON y asincronía
from dotenv import load_dotenv
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from typing import List, Dict, TypedDict
from contextlib import AsyncExitStack
import json
import asyncio

# Carga las variables de entorno desde el archivo .env
load_dotenv()

# Define la estructura de un Tool (herramienta) usando TypedDict para tipado estático
class ToolDefinition(TypedDict):
    name: str
    description: str
    input_schema: dict

# Clase principal del chatbot
class MCP_ChatBot:

    def __init__(self):
        # Inicializa la lista de sesiones, el stack de salida asíncrono, el cliente de Anthropic,
        # la lista de herramientas disponibles y el mapeo de herramientas a sesiones
        self.sessions: List[ClientSession] = [] # Lista de sesiones MCP activas
        self.exit_stack = AsyncExitStack() # Stack para manejar recursos asíncronos
        self.anthropic = Anthropic() # Cliente para la API de Anthropic
        self.available_tools: List[ToolDefinition] = [] # Lista de herramientas disponibles
        self.tool_to_session: Dict[str, ClientSession] = {} # Mapeo de nombre de herramienta a sesión MCP

    # Método para conectar a un servidor MCP individual
    async def connect_to_server(self, server_name: str, server_config: dict) -> None:
        """Conecta a un solo servidor MCP y registra sus herramientas."""
        try:
            # Crea los parámetros del servidor y establece la conexión usando el stack asíncrono
            server_params = StdioServerParameters(**server_config)
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read, write = stdio_transport
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()
            self.sessions.append(session)
            
            # Obtiene y muestra las herramientas disponibles en este servidor
            response = await session.list_tools()
            tools = response.tools
            print(f"\nConnected to {server_name} with tools:", [t.name for t in tools])
            
            # Registra cada herramienta y la asocia a la sesión correspondiente
            for tool in tools:
                self.tool_to_session[tool.name] = session
                self.available_tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                })
        except Exception as e:
            print(f"Failed to connect to {server_name}: {e}")

    # Método para conectar a todos los servidores MCP configurados
    async def connect_to_servers(self):
        """Conecta a todos los servidores MCP definidos en el archivo de configuración."""
        try:
            # Lee la configuración de servidores desde un archivo JSON
            with open("server_config.json", "r") as file:
                data = json.load(file)
            
            servers = data.get("mcpServers", {})
            
            # Conecta a cada servidor usando su configuración
            for server_name, server_config in servers.items():
                await self.connect_to_server(server_name, server_config)
        except Exception as e:
            print(f"Error loading server configuration: {e}")
            raise
    
    # Procesa una consulta del usuario, interactuando con el modelo y las herramientas
    async def process_query(self, query):
        # Inicializa la conversación con el mensaje del usuario
        messages = [{'role':'user', 'content':query}]
        # Solicita una respuesta al modelo de Anthropic, pasando las herramientas disponibles
        response = self.anthropic.messages.create(max_tokens = 2024,
                                      model = 'claude-3-7-sonnet-20250219', 
                                      tools = self.available_tools,
                                      messages = messages)
        process_query = True
        while process_query:
            assistant_content = []
            # Itera sobre el contenido de la respuesta del modelo
            for content in response.content:
                if content.type =='text':
                    # Si es texto, lo imprime y lo agrega al historial
                    print(content.text)
                    assistant_content.append(content)
                    if(len(response.content) == 1):
                        process_query= False
                elif content.type == 'tool_use':
                    # Si el modelo solicita usar una herramienta, prepara la llamada
                    assistant_content.append(content)
                    messages.append({'role':'assistant', 'content':assistant_content})
                    tool_id = content.id
                    tool_args = content.input
                    tool_name = content.name
                    
                    print(f"Calling tool {tool_name} with args {tool_args}")
                    
                    # Llama a la herramienta correspondiente usando la sesión asociada
                    session = self.tool_to_session[tool_name]
                    result = await session.call_tool(tool_name, arguments=tool_args)
                    # Agrega el resultado de la herramienta al historial de mensajes
                    messages.append({"role": "user", 
                                      "content": [
                                          {
                                              "type": "tool_result",
                                              "tool_use_id":tool_id,
                                              "content": result.content
                                          }
                                      ]
                                    })
                    # Solicita una nueva respuesta al modelo con el resultado de la herramienta
                    response = self.anthropic.messages.create(max_tokens = 2024,
                                      model = 'claude-3-7-sonnet-20250219', 
                                      tools = self.available_tools,
                                      messages = messages) 
                    
                    # Si la nueva respuesta es solo texto, la imprime y termina el ciclo
                    if(len(response.content) == 1 and response.content[0].type == "text"):
                        print(response.content[0].text)
                        process_query= False

    # Bucle principal de interacción con el usuario
    async def chat_loop(self):
        """Ejecuta un bucle interactivo para recibir consultas del usuario."""
        print("\nMCP Chatbot Iniciado!")
        print("Escribe tu consultas o 'salir' para salir.")
        
        while True:
            try:
                # Solicita una consulta al usuario
                query = input("\nConsulta: ").strip()

                if query.lower() == 'salir':
                    break
                    
                # Procesa la consulta usando el método anterior
                await self.process_query(query)
                print("\n")
                    
            except Exception as e:
                print(f"\nError: {str(e)}")
    
    # Limpia y cierra todos los recursos abiertos
    async def cleanup(self):
        """Cierra correctamente todos los recursos usando AsyncExitStack."""
        await self.exit_stack.aclose()

# Función principal que inicia el chatbot y gestiona el ciclo de vida
async def main():
    chatbot = MCP_ChatBot()
    try:
        # Conecta a los servidores y lanza el bucle de chat
        await chatbot.connect_to_servers()
        await chatbot.chat_loop()
    finally:
        # Limpia los recursos al finalizar
        await chatbot.cleanup()

# Punto de entrada del script: ejecuta la función principal usando asyncio
if __name__ == "__main__":
    asyncio.run(main())

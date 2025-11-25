import pygame
import sys
from typing import List, Tuple, Dict, Optional
import time
from dataclasses import dataclass
import threading
import openai
import os
import json
from pathlib import Path
from veu import voice_control  # Importamos el control de voz

# Configuración del chatbot
base_url = "https://api.aimlapi.com/v1"
api_key = os.getenv("API_KEY", "fa0e452867df46829a6434883a5b5d11")
system_prompt = "Eres un asistente inteligente. Responde de manera clara y útil a cualquier pregunta."

# Configura el cliente OpenAI
client = openai.OpenAI(
    base_url=base_url,
    api_key=api_key,
)

# Configuración inicial
pygame.init()
pygame.font.init()

# Constantes y tipos
@dataclass
class ColorTheme:
    background: Tuple[int, int, int]
    text: Tuple[int, int, int]
    input_box: Tuple[int, int, int]
    user_bubble: Tuple[int, int, int]
    bot_bubble: Tuple[int, int, int]
    button: Tuple[int, int, int]
    button_hover: Tuple[int, int, int]
    scroll_bar: Tuple[int, int, int]
    border: Tuple[int, int, int]

LIGHT_THEME = ColorTheme(
    background=(245, 245, 245),
    text=(50, 50, 50),
    input_box=(255, 255, 255),
    user_bubble=(220, 240, 255),
    bot_bubble=(240, 240, 240),
    button=(70, 130, 180),
    button_hover=(50, 110, 160),
    scroll_bar=(100, 150, 200),
    border=(200, 200, 200)
)

DARK_THEME = ColorTheme(
    background=(40, 40, 40),
    text=(240, 240, 240),
    input_box=(60, 60, 60),
    user_bubble=(50, 80, 120),
    bot_bubble=(80, 80, 80),
    button=(0, 150, 100),
    button_hover=(0, 130, 80),
    scroll_bar=(0, 180, 120),
    border=(100, 100, 100)
)

FONT_NAME = 'Segoe UI'
FONT_SMALL = 16
FONT_MEDIUM = 18
FONT_LARGE = 24
FONT_TITLE = 28

class ChatMessage:
    def __init__(self, sender: str, content: str):
        self.sender = sender
        self.content = content
        self.timestamp = time.strftime("%H:%M")
        self.lines: List[str] = []
        self.bubble_rect: Optional[pygame.Rect] = None

    def to_dict(self):
        return {
            'sender': self.sender,
            'content': self.content,
            'timestamp': self.timestamp
        }

    @classmethod
    def from_dict(cls, data: dict):
        message = cls(data['sender'], data['content'])
        message.timestamp = data['timestamp']
        return message

class ChatUI:
    def __init__(self):
        self.screen_width, self.screen_height = 1000, 700
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.RESIZABLE)
        pygame.display.set_caption('Asistente IA Profesional')
        
        # Fuentes
        self.font_small = pygame.font.SysFont(FONT_NAME, FONT_SMALL)
        self.font_medium = pygame.font.SysFont(FONT_NAME, FONT_MEDIUM)
        self.font_large = pygame.font.SysFont(FONT_NAME, FONT_LARGE)
        self.font_title = pygame.font.SysFont(FONT_NAME, FONT_TITLE, bold=True)
        self.font_bold = pygame.font.SysFont(FONT_NAME, FONT_MEDIUM, bold=True)
        
        # Estado de la aplicación
        self.theme = LIGHT_THEME
        self.color_mode = "claro"
        self.running = True
        self.menu_active = True
        self.input_active = False
        self.scrolling = False
        self.welcome_shown = False
        self.waiting_for_response = False
        self.showing_history = False
        
        # Elementos de la UI
        self.input_text = ""
        self.chat_history: List[ChatMessage] = []
        self.scroll_offset = 0
        self.chat_surface_height = 5000
        self.chat_surface = pygame.Surface((self.screen_width, self.chat_surface_height))
        
        # Rectángulos de UI
        self.input_box = pygame.Rect(30, self.screen_height - 80, self.screen_width - 110, 50)
        self.send_button = pygame.Rect(self.screen_width - 70, self.screen_height - 80, 50, 50)
        self.new_chat_button = pygame.Rect(self.screen_width - 200, 20, 160, 40)
        self.voice_button = pygame.Rect(self.screen_width - 270, 20, 60, 40)  # Botón de voz
        self.history_button = pygame.Rect(self.screen_width - 450, 20, 180, 40)  # Botón de historial
        
        # Cursor
        self.cursor_visible = True
        self.cursor_timer = 0
        self.cursor_blink_interval = 500
        
        # Historial de conversaciones
        self.conversation_history: List[List[ChatMessage]] = []
        self.load_conversation_history()

    def load_conversation_history(self):
        """Carga el historial de conversaciones desde el archivo JSON"""
        history_file = Path('chat_history.json')
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.conversation_history = [
                        [ChatMessage.from_dict(msg) for msg in conversation] 
                        for conversation in data
                    ]
                    # Mantener solo las 3 últimas conversaciones
                    self.conversation_history = self.conversation_history[-3:]
                    print(f"Historial cargado: {len(self.conversation_history)} conversaciones")
            except Exception as e:
                print(f"Error cargando historial: {e}")
                self.conversation_history = []

    def save_conversation_history(self):
        """Guarda el historial de conversaciones en el archivo JSON"""
        history_file = Path('chat_history.json')
        try:
            # Convertir todas las conversaciones a formato serializable
            data = [
                [msg.to_dict() for msg in conversation] 
                for conversation in self.conversation_history
            ]
            # Mantener solo las 3 últimas conversaciones
            data = data[-3:]
            
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Historial guardado: {len(data)} conversaciones")
        except Exception as e:
            print(f"Error guardando historial: {e}")

    def add_to_history(self):
        """Añade la conversación actual al historial"""
        if self.chat_history and len(self.chat_history) > 1:  # Solo guardar si hay conversación real
            # Añadir la conversación actual al historial
            self.conversation_history.append(self.chat_history.copy())
            # Mantener solo las 3 últimas conversaciones
            self.conversation_history = self.conversation_history[-3:]
            self.save_conversation_history()
            print(f"Conversación añadida al historial. Total: {len(self.conversation_history)}")

    def load_conversation(self, index: int):
        """Carga una conversación del historial"""
        if 0 <= index < len(self.conversation_history):
            self.chat_history = self.conversation_history[index].copy()
            for msg in self.chat_history:
                self.process_message_lines(msg)
            self.scroll_offset = 0
            self.menu_active = False
            self.welcome_shown = True
            self.showing_history = False
            print(f"Conversación {index} cargada")

    def handle_events(self):
        mouse_pos = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.add_to_history()
                self.running = False
            
            elif event.type == pygame.VIDEORESIZE:
                self.handle_resize(event.w, event.h)
            
            elif event.type == pygame.KEYDOWN:
                self.handle_keydown(event)
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.handle_mouse_down(event, mouse_pos)
            
            elif event.type == pygame.MOUSEBUTTONUP:
                self.scrolling = False
            
            elif event.type == pygame.MOUSEMOTION and self.scrolling:
                self.handle_scroll(event)
            
            elif event.type == pygame.MOUSEWHEEL:
                self.handle_mouse_wheel(event)
            
            elif event.type == pygame.USEREVENT and hasattr(event, "response"):
                self.waiting_for_response = False
                # Reemplaza "Escribiendo..." con la respuesta real
                if self.chat_history and self.chat_history[-1].content == "Escribiendo...":
                    self.chat_history[-1].content = event.response
                    self.process_message_lines(self.chat_history[-1])
                else:
                    self.add_message("Asistente", event.response)
                self.scroll_offset = max(0, self.chat_surface.get_height() - (self.screen_height - 120))
        
        self.update_cursor()

    def handle_resize(self, width: int, height: int):
        self.screen_width, self.screen_height = width, height
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        self.input_box.y = height - 80
        self.input_box.width = width - 110
        self.send_button.y = height - 80
        self.send_button.x = width - 70
        self.new_chat_button.x = width - 200
        self.voice_button.x = width - 270
        self.history_button.x = width - 450
        self.chat_surface = pygame.Surface((width, self.chat_surface_height))

    def handle_keydown(self, event):
        if event.key == pygame.K_TAB:
            self.toggle_theme()
        elif event.key == pygame.K_v and not self.input_active:  
            voice_active = voice_control.toggle()
            self.add_message("Sistema", f"Voz {'activada' if voice_active else 'desactivada'}")
        elif self.showing_history:
            if event.key == pygame.K_b or event.key == pygame.K_ESCAPE:
                self.showing_history = False
            elif event.key in [pygame.K_1, pygame.K_2, pygame.K_3]:
                index = event.key - pygame.K_1
                if index < len(self.conversation_history):
                    self.load_conversation(index)
        elif self.menu_active:
            if event.key == pygame.K_c:
                self.start_chat()
            elif event.key == pygame.K_h:
                self.show_history_menu()
            elif event.key == pygame.K_q:
                self.running = False
        elif self.input_active and not self.waiting_for_response:
            if event.key == pygame.K_RETURN and self.input_text.strip():
                self.send_message()
            elif event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            else:
                self.input_text += event.unicode

    def handle_mouse_down(self, event, mouse_pos):
        if self.showing_history:
            # Manejar clic en el menú de historial
            for i in range(len(self.conversation_history)):
                option_rect = pygame.Rect(self.screen_width//2 - 200, 180 + i * 50, 400, 40)
                if option_rect.collidepoint(mouse_pos):
                    self.load_conversation(i)
                    return
            
            # Verificar si se hace clic fuera del menú
            back_rect = pygame.Rect(self.screen_width//2 - 100, 300 + len(self.conversation_history) * 50, 200, 40)
            if not back_rect.collidepoint(mouse_pos):
                self.showing_history = False
            return

        if self.input_box.collidepoint(mouse_pos) and not self.waiting_for_response:
            self.input_active = True
        else:
            self.input_active = False
        
        if self.send_button.collidepoint(mouse_pos) and self.input_text.strip() and not self.waiting_for_response:
            self.send_message()
        elif self.voice_button.collidepoint(mouse_pos) and not self.input_active:
            voice_active = voice_control.toggle()
            self.add_message("Sistema", f"Voz {'activada' if voice_active else 'desactivada'}")
        elif self.new_chat_button.collidepoint(mouse_pos) and not self.menu_active and not self.waiting_for_response:
            self.add_to_history()
            self.reset_chat()
        elif self.history_button.collidepoint(mouse_pos) and not self.waiting_for_response:
            self.show_history_menu()
        elif event.button == 1:  # Clic izquierdo para scroll
            self.scrolling = True
            self.scroll_start_pos = mouse_pos[1]
            self.scroll_start_offset = self.scroll_offset

    def show_history_menu(self):
        """Muestra el menú de historial de conversaciones"""
        if not self.conversation_history:
            self.add_message("Sistema", "No hay conversaciones anteriores guardadas.")
            return
        
        self.showing_history = True
        print("Mostrando menú de historial")

    def handle_scroll(self, event):
        if not self.showing_history:  # Solo permitir scroll si no estamos en el menú de historial
            dy = event.pos[1] - self.scroll_start_pos
            max_scroll = self.chat_surface.get_height() - (self.screen_height - 120)
            self.scroll_offset = min(max(self.scroll_start_offset + dy, 0), max_scroll)

    def handle_mouse_wheel(self, event):
        if not self.showing_history:  # Solo permitir scroll si no estamos en el menú de historial
            self.scroll_offset -= event.y * 30
            max_scroll = self.chat_surface.get_height() - (self.screen_height - 120)
            self.scroll_offset = max(0, min(self.scroll_offset, max_scroll))

    def update_cursor(self):
        self.cursor_timer += pygame.time.Clock().tick(60)
        if self.cursor_timer >= self.cursor_blink_interval:
            self.cursor_visible = not self.cursor_visible
            self.cursor_timer = 0

    def toggle_theme(self):
        self.color_mode = "oscuro" if self.color_mode == "claro" else "claro"
        self.theme = DARK_THEME if self.color_mode == "oscuro" else LIGHT_THEME

    def start_chat(self):
        self.menu_active = False
        if not self.welcome_shown:
            self.add_message("Asistente", "Hola, ¿en qué puedo ayudarte hoy?")
            self.welcome_shown = True

    def reset_chat(self):
        """Reinicia el chat actual"""
        self.add_to_history()  # Guardar la conversación actual antes de reiniciar
        self.menu_active = True
        self.chat_history.clear()
        self.input_text = ""
        self.welcome_shown = False
        self.scroll_offset = 0
        self.waiting_for_response = False
        print("Chat reiniciado")

    def send_message(self):
        user_input = self.input_text.strip()
        if user_input:
            self.add_message("Tú", user_input)
            self.input_text = ""
            self.waiting_for_response = True
            self.add_message("Asistente", "Escribiendo...")
            
            def get_bot_response_thread():
                try:
                    formatted_history = [
                        f"{msg.sender}: {msg.content}" 
                        for msg in self.chat_history 
                        if msg.content != "Escribiendo..."
                    ]
                    bot_response = get_bot_response(formatted_history)
                    
                    if not bot_response:
                        bot_response = "No se pudo obtener una respuesta."
                    
                    if voice_control.active:
                        voice_control.speak(bot_response)
                    
                    response_event = pygame.event.Event(
                        pygame.USEREVENT, 
                        {"response": bot_response}
                    )
                    pygame.event.post(response_event)
                
                except Exception as e:
                    error_event = pygame.event.Event(
                        pygame.USEREVENT,
                        {"response": f"Error: {str(e)}"}
                    )
                    pygame.event.post(error_event)
            
            threading.Thread(target=get_bot_response_thread, daemon=True).start()

    def add_message(self, sender: str, content: str):
        message = ChatMessage(sender, content)
        self.chat_history.append(message)
        self.process_message_lines(message)

    def process_message_lines(self, message: ChatMessage):
        bubble_margin = 30
        max_bubble_width = self.screen_width - 2 * bubble_margin - 40
        
        words = message.content.split(' ')
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            if self.font_medium.size(test_line)[0] <= max_bubble_width:
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        message.lines = lines
        
        total_height = sum(20 + len(msg.lines) * self.font_medium.get_linesize() + 40 for msg in self.chat_history)
        self.chat_surface_height = max(total_height + 100, self.screen_height)
        self.chat_surface = pygame.Surface((self.screen_width, self.chat_surface_height))

    def render(self):
        self.screen.fill(self.theme.background)
        
        if self.showing_history:
            self.render_history_menu()
        elif self.menu_active:
            self.render_main_menu()
        else:
            self.render_chat()
            self.render_input_area()
        
        pygame.display.flip()

    def render_main_menu(self):
        title = self.font_title.render("Asistente IA Profesional", True, self.theme.button)
        self.screen.blit(title, (self.screen_width//2 - title.get_width()//2, 150))
        
        subtitle = self.font_large.render("Tu asistente personal inteligente", True, self.theme.text)
        self.screen.blit(subtitle, (self.screen_width//2 - subtitle.get_width()//2, 210))
        
        options = [
            "Presiona 'C' para comenzar una conversación",
            "Presiona 'H' para ver el historial de conversaciones",
            "Presiona 'Q' para salir del programa",
            "Cambia entre temas claro/oscuro con TAB",
            "Activa/desactiva voz con V",
            "Escribe tu mensaje y presiona Enter para enviar"
        ]
        
        for i, option in enumerate(options):
            text = self.font_medium.render(option, True, self.theme.text)
            self.screen.blit(text, (self.screen_width//2 - text.get_width()//2, 300 + i * 40))

    def render_history_menu(self):
        """Renderiza el menú de historial de conversaciones"""
        title = self.font_title.render("Historial de Conversaciones", True, self.theme.button)
        self.screen.blit(title, (self.screen_width//2 - title.get_width()//2, 100))
        
        if not self.conversation_history:
            no_history = self.font_medium.render("No hay conversaciones guardadas", True, self.theme.text)
            self.screen.blit(no_history, (self.screen_width//2 - no_history.get_width()//2, 200))
        else:
            for i, conversation in enumerate(self.conversation_history):
                if conversation:
                    # Obtener el primer mensaje como preview
                    first_message = conversation[0].content[:50] + "..." if len(conversation[0].content) > 50 else conversation[0].content
                    date = conversation[0].timestamp
                    message_count = len(conversation)
                    
                    text = f"{i+1}. {date} - {first_message} ({message_count} mensajes)"
                    text_surface = self.font_medium.render(text, True, self.theme.text)
                    
                    # Crear un rectángulo para la opción
                    option_rect = pygame.Rect(self.screen_width//2 - 200, 180 + i * 50, 400, 40)
                    
                    # Resaltar si el mouse está sobre la opción
                    if option_rect.collidepoint(pygame.mouse.get_pos()):
                        pygame.draw.rect(self.screen, self.theme.button, option_rect, border_radius=8)
                    
                    self.screen.blit(text_surface, (option_rect.x + 10, option_rect.y + 10))
        
        # Botón para volver
        back_rect = pygame.Rect(self.screen_width//2 - 100, 300 + len(self.conversation_history) * 50, 200, 40)
        pygame.draw.rect(self.screen, self.theme.button, back_rect, border_radius=8)
        back_text = self.font_medium.render("Volver (B o ESC)", True, self.theme.background)
        self.screen.blit(back_text, (back_rect.centerx - back_text.get_width()//2, back_rect.centery - back_text.get_height()//2))

    def render_chat(self):
        self.chat_surface.fill(self.theme.background)
        
        y_offset = 20
        bubble_margin = 30
        max_bubble_width = self.screen_width - 2 * bubble_margin - 40
        
        for message in self.chat_history:
            is_user = message.sender == "Tú"
            bubble_color = self.theme.user_bubble if is_user else self.theme.bot_bubble
            text_color = self.theme.text
            
            line_height = self.font_medium.get_linesize()
            bubble_height = len(message.lines) * line_height + 40
            if message.lines:
                bubble_width = min(max(self.font_medium.size(line)[0] for line in message.lines) + 40, max_bubble_width)
            else:
                bubble_width = 120
            
            bubble_x = self.screen_width - bubble_width - bubble_margin if is_user else bubble_margin
            
            message.bubble_rect = pygame.Rect(bubble_x, y_offset, bubble_width, bubble_height)
            pygame.draw.rect(self.chat_surface, bubble_color, message.bubble_rect, border_radius=15)
            
            sender_text = f"{message.sender} • {message.timestamp}"
            sender_surface = self.font_bold.render(sender_text, True, text_color)
            self.chat_surface.blit(sender_surface, (bubble_x + 20, y_offset + 15))
            
            for i, line in enumerate(message.lines):
                line_surface = self.font_medium.render(line, True, text_color)
                self.chat_surface.blit(line_surface, (bubble_x + 20, y_offset + 40 + i * line_height))
            
            y_offset += bubble_height + 20
        
        visible_height = self.screen_height - 130
        self.screen.blit(self.chat_surface, (0, 0), (0, self.scroll_offset, self.screen_width, visible_height))
        
        self.render_scroll_bar(y_offset, visible_height)

    def render_scroll_bar(self, content_height: int, visible_height: int):
        if content_height > visible_height:
            scroll_ratio = visible_height / content_height
            scroll_bar_height = max(int(scroll_ratio * visible_height), 30)
            scroll_pos = (self.scroll_offset / content_height) * visible_height
            
            scroll_bar = pygame.Rect(self.screen_width - 8, scroll_pos, 6, scroll_bar_height)
            pygame.draw.rect(self.screen, self.theme.scroll_bar, scroll_bar, border_radius=3)

    def render_input_area(self):
        pygame.draw.rect(self.screen, self.theme.input_box, (0, self.screen_height - 90, self.screen_width, 90))
        
        input_box_color = self.theme.input_box
        border_color = self.theme.button if self.input_active else self.theme.border
        
        pygame.draw.rect(self.screen, input_box_color, self.input_box, border_radius=12)
        pygame.draw.rect(self.screen, border_color, self.input_box, 2, border_radius=12)
        
        input_surface = self.font_medium.render(self.input_text, True, self.theme.text)
        self.screen.blit(input_surface, (self.input_box.x + 15, self.input_box.y + 15))
        
        if self.input_active and self.cursor_visible and not self.waiting_for_response:
            cursor_x = self.input_box.x + 15 + input_surface.get_width()
            pygame.draw.line(self.screen, self.theme.text,
                           (cursor_x, self.input_box.y + 15),
                           (cursor_x, self.input_box.y + 35), 2)
        
        # Botón enviar
        send_color = self.theme.button_hover if self.send_button.collidepoint(pygame.mouse.get_pos()) and not self.waiting_for_response else (150, 150, 150)
        pygame.draw.rect(self.screen, send_color, self.send_button, border_radius=12)
        send_icon = self.font_large.render("→", True, self.theme.background)
        self.screen.blit(send_icon, (self.send_button.centerx - send_icon.get_width()//2,
                                   self.send_button.centery - send_icon.get_height()//2))
        
        # Botón nueva conversación
        new_chat_color = self.theme.button_hover if self.new_chat_button.collidepoint(pygame.mouse.get_pos()) and not self.waiting_for_response else (150, 150, 150)
        pygame.draw.rect(self.screen, new_chat_color, self.new_chat_button, border_radius=20)
        new_chat_text = self.font_medium.render("Nueva Conversación", True, self.theme.background)
        self.screen.blit(new_chat_text, (self.new_chat_button.centerx - new_chat_text.get_width()//2,
                                        self.new_chat_button.centery - new_chat_text.get_height()//2))
        
        # Botón de voz
        voice_color = (0, 200, 0) if voice_control.active else (200, 0, 0)
        pygame.draw.rect(self.screen, voice_color, self.voice_button, border_radius=20)
        voice_text = self.font_medium.render("Voz", True, self.theme.background)
        self.screen.blit(voice_text, (self.voice_button.centerx - voice_text.get_width()//2,
                                    self.voice_button.centery - voice_text.get_height()//2))
        
        # Botón de historial
        history_color = self.theme.button_hover if self.history_button.collidepoint(pygame.mouse.get_pos()) and not self.waiting_for_response else self.theme.button
        pygame.draw.rect(self.screen, history_color, self.history_button, border_radius=20)
        history_text = self.font_medium.render("Ver Historial", True, self.theme.background)
        self.screen.blit(history_text, (self.history_button.centerx - history_text.get_width()//2,
                                      self.history_button.centery - history_text.get_height()//2))

    def run(self):
        clock = pygame.time.Clock()
        
        while self.running:
            self.handle_events()
            self.render()
            clock.tick(60)
        
        self.add_to_history()
        pygame.quit()
        sys.exit()

def get_bot_response(chat_history):
    try:
        messages = [{"role": "system", "content": system_prompt}]
        for msg in chat_history:
            if msg.startswith("Tú: "):
                messages.append({"role": "user", "content": msg[4:]})
            elif msg.startswith("Asistente: "):
                messages.append({"role": "assistant", "content": msg[10:]})
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
            max_tokens=256,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        error_str = str(e)
        if "403" in error_str and "insufficient_resource" in error_str:
            return "Límite de uso alcanzado: Has agotado tu cuota de solicitudes. Por favor, actualiza tu método de pago para continuar usando el servicio."
        elif "rate limit" in error_str.lower() or "busy" in error_str.lower():
            return "El servidor está ocupado, por favor inténtalo de nuevo más tarde."
        elif "404" in error_str:
            return "Error: Recurso no encontrado (404)"
        elif "401" in error_str:
            return "Error: No autorizado (comprueba tu API key)"
        elif "304" in error_str:
            return "Error: No se pudo modificar el recurso (304)"
        elif "500" in error_str:
            return "Error interno del servidor (500)"
        elif "502" in error_str or "503" in error_str or "504" in error_str:
            return "Problemas de conexión con el servidor. Por favor, inténtalo de nuevo más tarde."
        else:
            return "Se produjo un error inesperado. Por favor, inténtalo de nuevo más tarde."

if __name__ == "__main__":
    app = ChatUI()
    app.run()
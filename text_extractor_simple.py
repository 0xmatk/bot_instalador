# -*- coding: utf-8 -*-
import cv2
import numpy as np
import pyautogui
from PIL import Image, ImageDraw
import win32gui
import win32con
import re

class SimpleTextExtractor:
    def __init__(self):
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.5
        
        # Plantillas comunes de texto en botones (sin OCR)
        self.button_templates = {
            'next': ['next', 'siguiente', 'continuar', '>'],
            'install': ['install', 'instalar', 'setup'],
            'cancel': ['cancel', 'cancelar', 'salir'],
            'accept': ['accept', 'aceptar', 'ok', 'si'],
            'finish': ['finish', 'finalizar', 'done'],
            'back': ['back', 'atras', 'volver', '<'],
            'browse': ['browse', 'examinar', '...'],
            'close': ['close', 'cerrar', 'x']
        }
    
    def take_screenshot(self, region=None):
        """Tomar captura de pantalla"""
        try:
            screenshot = pyautogui.screenshot(region=region)
            return np.array(screenshot)
        except Exception as e:
            print(f"Error tomando screenshot: {e}")
            return None
    
    def list_all_windows(self):
        """Listar todas las ventanas visibles"""
        def enum_windows_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                window_text = win32gui.GetWindowText(hwnd)
                class_name = win32gui.GetClassName(hwnd)
                if window_text:  # Solo ventanas con título
                    windows.append({
                        'handle': hwnd,
                        'title': window_text,
                        'class': class_name
                    })
            return True
        
        windows = []
        win32gui.EnumWindows(enum_windows_callback, windows)
        return windows
    
    def find_installation_window(self):
        """Buscar ventana de instalación automáticamente"""
        windows = self.list_all_windows()
        
        # Palabras clave que indican ventanas de instalación
        installation_keywords = [
            'setup', 'install', 'wizard', 'installer', 'configurar',
            'instalar', 'asistente', 'installation', 'instalacion'
        ]
        
        for window in windows:
            title_lower = window['title'].lower()
            for keyword in installation_keywords:
                if keyword in title_lower:
                    return window['handle']
        
        return None
    
    def take_window_screenshot(self, hwnd=None):
        """Tomar captura de una ventana específica"""
        try:
            if hwnd is None:
                # Primero intentar encontrar ventana de instalación
                hwnd = self.find_installation_window()
                if hwnd is None:
                    # Si no encuentra, usar ventana activa
                    hwnd = win32gui.GetForegroundWindow()
            
            # Traer ventana al frente
            win32gui.SetForegroundWindow(hwnd)
            
            window_rect = win32gui.GetWindowRect(hwnd)
            window_title = win32gui.GetWindowText(hwnd)
            
            print(f"Capturando ventana: '{window_title}'")
            print(f"Coordenadas: {window_rect}")
            
            # Crear región de la ventana
            region = (
                window_rect[0],  # x
                window_rect[1],  # y  
                window_rect[2] - window_rect[0],  # width
                window_rect[3] - window_rect[1]   # height
            )
            
            # Verificar que la región sea válida
            if region[2] <= 0 or region[3] <= 0:
                print("Región inválida, usando screenshot completo")
                return self.take_screenshot()
            
            screenshot = pyautogui.screenshot(region=region)
            return np.array(screenshot)
        except Exception as e:
            print(f"Error tomando screenshot de ventana: {e}")
            return self.take_screenshot()  # Fallback a screenshot completo
    
    def get_window_text_win32(self):
        """Extraer texto usando Win32 API (más confiable que OCR)"""
        try:
            def enum_child_windows(hwnd, window_text):
                text = win32gui.GetWindowText(hwnd)
                class_name = win32gui.GetClassName(hwnd)
                if text:
                    window_text.append({
                        'text': text,
                        'class': class_name,
                        'handle': hwnd
                    })
                return True
            
            hwnd = win32gui.GetForegroundWindow()
            window_text = []
            
            # Obtener texto de la ventana principal
            main_text = win32gui.GetWindowText(hwnd)
            main_class = win32gui.GetClassName(hwnd)
            if main_text:
                window_text.append({
                    'text': main_text,
                    'class': main_class,
                    'handle': hwnd
                })
            
            # Obtener texto de controles hijos
            win32gui.EnumChildWindows(hwnd, enum_child_windows, window_text)
            
            return window_text
        except Exception as e:
            print(f"Error obteniendo texto Win32: {e}")
            return []
    
    def get_detailed_window_info(self):
        """Obtener información detallada de la ventana"""
        controls = self.get_window_text_win32()
        
        print("=== CONTROLES DETECTADOS ===")
        for i, control in enumerate(controls):
            try:
                clean_text = control['text'].encode('ascii', 'ignore').decode('ascii')
                print(f"{i+1}. Clase: {control['class']}")
                print(f"   Texto: '{clean_text}'")
                print(f"   Handle: {control['handle']}")
                print()
            except:
                print(f"{i+1}. [Control con caracteres especiales]")
        
        return controls
    
    def get_control_position(self, hwnd):
        """Obtener posición de un control"""
        try:
            rect = win32gui.GetWindowRect(hwnd)
            return {
                'x': rect[0], 'y': rect[1],
                'width': rect[2] - rect[0],
                'height': rect[3] - rect[1]
            }
        except:
            return None
    
    def visualize_detected_controls(self, filename="detected_controls.png"):
        """Crear imagen visual de los controles detectados"""
        controls = self.get_window_text_win32()
        screenshot = self.take_window_screenshot()  # Usar screenshot de ventana
        
        if screenshot is None:
            print("No se pudo tomar screenshot")
            return False
        
        img = Image.fromarray(screenshot)
        draw = ImageDraw.Draw(img)
        
        # Obtener posición de la ventana principal
        main_hwnd = win32gui.GetForegroundWindow()
        main_rect = win32gui.GetWindowRect(main_hwnd)
        
        detected_count = 0
        
        for i, control in enumerate(controls):
            pos = self.get_control_position(control['handle'])
            if pos and pos['width'] > 0 and pos['height'] > 0:
                # Convertir coordenadas absolutas a relativas de la ventana
                x = pos['x'] - main_rect[0]
                y = pos['y'] - main_rect[1]
                w = pos['width']
                h = pos['height']
                
                # Solo dibujar si está dentro de la ventana
                if x >= -50 and y >= -50 and x <= img.width + 50 and y <= img.height + 50:
                    detected_count += 1
                    
                    # Color según tipo de control
                    color = 'red'
                    if 'Button' in control['class']:
                        color = 'green'
                    elif 'Static' in control['class']:
                        color = 'blue'
                    elif 'Edit' in control['class']:
                        color = 'orange'
                    elif 'Chrome' in control['class']:
                        color = 'purple'
                    
                    # Dibujar rectángulo
                    draw.rectangle([x, y, x + w, y + h], outline=color, width=2)
                    
                    # Agregar etiqueta con número
                    draw.text((x, y - 15), f"{i+1}", fill=color)
                    
                    # Agregar texto del control si cabe
                    try:
                        clean_text = control['text'].encode('ascii', 'ignore').decode('ascii')
                        if len(clean_text) > 0 and w > 50:  # Solo si hay espacio
                            text_to_show = clean_text[:20] + "..." if len(clean_text) > 20 else clean_text
                            draw.text((x + 5, y + 5), text_to_show, fill=color)
                    except:
                        pass
        
        img.save(filename)
        print(f"Visualización guardada como: {filename}")
        print(f"Controles visualizados: {detected_count} de {len(controls)}")
        return True
    
    def detect_button_regions(self):
        """Detectar regiones de botones por forma y ubicación"""
        screenshot = self.take_window_screenshot()  # Usar screenshot de ventana
        if screenshot is None:
            return []
        
        # Convertir a escala de grises
        gray = cv2.cvtColor(screenshot, cv2.COLOR_RGB2GRAY)
        
        # Detectar bordes
        edges = cv2.Canny(gray, 50, 150)
        
        # Encontrar contornos rectangulares
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        button_regions = []
        for contour in contours:
            # Aproximar contorno a rectángulo
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            if len(approx) == 4:  # Es un rectángulo
                x, y, w, h = cv2.boundingRect(contour)
                
                # Filtrar por tamaño típico de botón
                if 50 <= w <= 200 and 20 <= h <= 50:
                    button_regions.append({
                        'x': x, 'y': y, 'width': w, 'height': h,
                        'center_x': x + w//2, 'center_y': y + h//2
                    })
        
        return button_regions
    
    def classify_buttons_by_position(self, button_regions):
        """Clasificar botones según su posición en la ventana"""
        if not button_regions:
            return []
        
        # Obtener dimensiones de pantalla
        screenshot = self.take_screenshot()
        screen_height, screen_width = screenshot.shape[:2]
        
        classified_buttons = []
        
        for region in button_regions:
            button_type = 'unknown'
            
            # Clasificar por posición vertical
            y_ratio = region['center_y'] / screen_height
            x_ratio = region['center_x'] / screen_width
            
            # Botones en la parte inferior (típicos Next/Cancel)
            if y_ratio > 0.8:
                if x_ratio > 0.7:  # Derecha
                    button_type = 'next'
                elif x_ratio < 0.3:  # Izquierda
                    button_type = 'back'
                else:  # Centro
                    button_type = 'accept'
            
            # Botones en la parte media
            elif 0.3 < y_ratio < 0.7:
                if x_ratio > 0.8:  # Muy a la derecha
                    button_type = 'browse'
                else:
                    button_type = 'install'
            
            region['predicted_type'] = button_type
            classified_buttons.append(region)
        
        return classified_buttons
    
    def find_installation_elements(self):
        """Buscar elementos típicos de instaladores sin OCR"""
        # Combinar detección Win32 y análisis de posición
        controls = self.get_window_text_win32()
        button_regions = self.detect_button_regions()
        classified_buttons = self.classify_buttons_by_position(button_regions)
        
        # Crear texto combinado para búsqueda
        all_text = ' '.join([control['text'] for control in controls if control.get('text')])
        
        # Mejorar clasificación con texto Win32
        for button in classified_buttons:
            for button_type, keywords in self.button_templates.items():
                if any(keyword.lower() in all_text.lower() for keyword in keywords):
                    button['has_text_match'] = True
                    button['text_match_type'] = button_type
                    break
        
        return classified_buttons
    
    def get_installation_progress(self):
        """Detectar progreso sin OCR"""
        controls = self.get_window_text_win32()
        all_text = ' '.join([control['text'] for control in controls if control.get('text')])
        
        progress_info = {
            'percentage': None,
            'status': 'unknown',
            'is_installing': False
        }
        
        # Buscar patrones de progreso en texto Win32
        percentage_match = re.search(r'(\d+)%', all_text)
        if percentage_match:
            progress_info['percentage'] = int(percentage_match.group(1))
        
        # Detectar palabras clave de instalación
        install_keywords = ['installing', 'instalando', 'copying', 'copiando', 
                           'extracting', 'extrayendo', 'configuring', 'configurando']
        
        for keyword in install_keywords:
            if keyword.lower() in all_text.lower():
                progress_info['is_installing'] = True
                progress_info['status'] = keyword
                break
        
        return progress_info
    
    def save_analysis(self, elements, filename="button_analysis.png"):
        """Guardar análisis visual de botones detectados"""
        screenshot = self.take_screenshot()
        if screenshot is None:
            return False
        
        img = Image.fromarray(screenshot)
        draw = ImageDraw.Draw(img)
        
        for element in elements:
            x, y, w, h = element['x'], element['y'], element['width'], element['height']
            
            # Color según tipo predicho
            color = 'red'
            if element.get('predicted_type') == 'next':
                color = 'green'
            elif element.get('predicted_type') == 'back':
                color = 'blue'
            elif element.get('predicted_type') == 'install':
                color = 'orange'
            
            # Dibujar rectángulo
            draw.rectangle([x, y, x + w, y + h], outline=color, width=3)
            
            # Etiqueta
            label = element.get('predicted_type', 'unknown')
            if element.get('has_text_match'):
                label += f" ({element.get('text_match_type')})"
            
            draw.text((x, y - 20), label, fill=color)
        
        img.save(filename)
        print(f"Análisis guardado como: {filename}")
        return True

# Ejemplo de uso
if __name__ == "__main__":
    extractor = SimpleTextExtractor()
    
    # Mostrar todas las ventanas disponibles
    print("=== VENTANAS DISPONIBLES ===")
    windows = extractor.list_all_windows()
    for i, window in enumerate(windows):
        try:
            clean_title = window['title'].encode('ascii', 'ignore').decode('ascii')
            print(f"{i+1}. {clean_title} ({window['class']})")
        except:
            print(f"{i+1}. [Título con caracteres especiales] ({window['class']})")
    
    # Buscar ventana de instalación
    install_hwnd = extractor.find_installation_window()
    if install_hwnd:
        install_title = win32gui.GetWindowText(install_hwnd)
        print(f"\n*** VENTANA DE INSTALACIÓN ENCONTRADA: {install_title} ***")
    else:
        print("\n*** NO SE ENCONTRÓ VENTANA DE INSTALACIÓN ***")
        print("Usando ventana activa por defecto...")
    
    print("\n=== CONTROLES DETECTADOS ===")
    # Mostrar información detallada de controles
    extractor.get_detailed_window_info()
    
    print("\n=== Creando visualización de controles ===")
    extractor.visualize_detected_controls()
    
    print("\n=== Detectando elementos de instalación ===")
    elements = extractor.find_installation_elements()
    print(f"Encontrados {len(elements)} elementos:")
    
    for element in elements:
        print(f"- Botón predicho: '{element['predicted_type']}' en ({element['x']}, {element['y']})")
        if element.get('has_text_match'):
            print(f"  |-- Coincide con texto: {element['text_match_type']}")
    
    print("\n=== Verificando progreso de instalación ===")
    progress = extractor.get_installation_progress()
    print(f"Estado: {progress['status']}")
    print(f"Instalando: {progress['is_installing']}")
    if progress['percentage']:
        print(f"Progreso: {progress['percentage']}%")
    
    # Guardar análisis visual
    if elements:
        extractor.save_analysis(elements)
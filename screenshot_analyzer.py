import cv2
import numpy as np
import pyautogui
from PIL import Image, ImageDraw
import time
import win32gui
import win32con

class ScreenshotAnalyzer:
    def __init__(self):
        # Configurar pyautogui
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.5
    
    def take_screenshot(self, region=None):
        """Tomar captura de pantalla completa o de region especifica"""
        try:
            screenshot = pyautogui.screenshot(region=region)
            return np.array(screenshot)
        except Exception as e:
            print(f"Error tomando screenshot: {e}")
            return None
    
    def get_active_window_info(self):
        """Obtener informacion de la ventana activa"""
        try:
            hwnd = win32gui.GetForegroundWindow()
            window_rect = win32gui.GetWindowRect(hwnd)
            window_title = win32gui.GetWindowText(hwnd)
            
            return {
                'handle': hwnd,
                'title': window_title,
                'rect': window_rect,
                'width': window_rect[2] - window_rect[0],
                'height': window_rect[3] - window_rect[1]
            }
        except Exception as e:
            print(f"Error obteniendo ventana activa: {e}")
            return None
    
    def find_buttons_by_color(self, image, button_color_range):
        """Detectar botones por rango de color con filtros mejorados"""
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        mask = cv2.inRange(hsv, button_color_range[0], button_color_range[1])
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        buttons = []
        image_height, image_width = image.shape[:2]
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # Filtros más estrictos para botones reales
            # Tamaño: botones típicos entre 60-300px ancho, 20-80px alto
            if (60 <= w <= 300 and 20 <= h <= 80 and
                # No debe ser demasiado grande (evitar ventanas completas)
                w < image_width * 0.4 and h < image_height * 0.3 and
                # Relación aspecto razonable para botones (no muy alargados)
                2 <= w/h <= 8):
                
                # Verificar que no esté en los bordes (botones están dentro de ventanas)
                margin = 10
                if (x > margin and y > margin and 
                    x + w < image_width - margin and 
                    y + h < image_height - margin):
                    
                    buttons.append({
                        'x': x, 
                        'y': y, 
                        'width': w, 
                        'height': h,
                        'area': w * h,
                        'aspect_ratio': w / h
                    })
        
        # Ordenar por tamaño (botones más pequeños primero, más probable que sean reales)
        buttons.sort(key=lambda b: b['area'])
        return buttons
    
    def find_template(self, template_path, threshold=0.8):
        """Buscar template de imagen en pantalla"""
        screenshot = self.take_screenshot()
        if screenshot is None:
            return None
            
        template = cv2.imread(template_path)
        if template is None:
            print(f"No se pudo cargar template: {template_path}")
            return None
        
        # Convertir a escala de grises
        gray_screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2GRAY)
        gray_template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        
        # Buscar template
        result = cv2.matchTemplate(gray_screenshot, gray_template, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= threshold)
        
        matches = []
        for pt in zip(*locations[::-1]):
            matches.append({
                'x': pt[0],
                'y': pt[1],
                'width': gray_template.shape[1],
                'height': gray_template.shape[0],
                'confidence': result[pt[1], pt[0]]
            })
        
        return matches
    
    def detect_ui_elements(self):
        """Detectar elementos basicos de UI con filtros mejorados"""
        screenshot = self.take_screenshot()
        if screenshot is None:
            return []
        
        elements = []
        
        # Rangos de color más específicos para botones reales
        color_ranges = [
            # Azules (botones Windows típicos)
            ([100, 100, 150], [130, 255, 255], 'blue'),
            
            # Grises claros (botones estándar)
            ([0, 0, 200], [180, 30, 255], 'gray_light'),
            
            # Grises medios 
            ([0, 0, 120], [180, 50, 200], 'gray_medium'),
            
            # Blancos/Plateados (Windows 11)
            ([0, 0, 240], [180, 15, 255], 'white'),
        ]
        
        all_detected = []
        
        for min_range, max_range, color_name in color_ranges:
            buttons = self.find_buttons_by_color(screenshot, (np.array(min_range), np.array(max_range)))
            for btn in buttons:
                btn['type'] = 'button'
                btn['color'] = color_name
                all_detected.append(btn)
        
        # Eliminar duplicados (botones muy cercanos entre sí)
        filtered_elements = []
        for btn in all_detected:
            is_duplicate = False
            for existing in filtered_elements:
                # Si están muy cerca, considerar como duplicado
                distance = ((btn['x'] - existing['x'])**2 + (btn['y'] - existing['y'])**2)**0.5
                overlap_x = max(0, min(btn['x'] + btn['width'], existing['x'] + existing['width']) - max(btn['x'], existing['x']))
                overlap_y = max(0, min(btn['y'] + btn['height'], existing['y'] + existing['height']) - max(btn['y'], existing['y']))
                overlap_area = overlap_x * overlap_y
                
                if distance < 30 or overlap_area > 0:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                filtered_elements.append(btn)
        
        # Ordenar por posición (izq-derecha, arriba-abajo) para mejor orden de click
        filtered_elements.sort(key=lambda e: (e['y'], e['x']))
        
        # Agregar detección por bordes como método adicional
        edge_buttons = self.detect_buttons_by_edges(screenshot)
        
        # Combinar ambos métodos y eliminar duplicados finales
        all_buttons = filtered_elements + edge_buttons
        final_elements = []
        
        for btn in all_buttons:
            is_duplicate = False
            for existing in final_elements:
                distance = ((btn['x'] - existing['x'])**2 + (btn['y'] - existing['y'])**2)**0.5
                if distance < 50:  # Si están muy cerca, es duplicado
                    is_duplicate = True
                    break
            if not is_duplicate:
                final_elements.append(btn)
        
        # Ordenar y limitar
        final_elements.sort(key=lambda e: (e['y'], e['x']))
        return final_elements[:8]  # Máximo 8 elementos
    
    def detect_buttons_by_edges(self, screenshot):
        """Detectar botones usando detección de bordes"""
        try:
            # Convertir a escala de grises
            gray = cv2.cvtColor(screenshot, cv2.COLOR_RGB2GRAY)
            
            # Aplicar blur para suavizar
            blurred = cv2.GaussianBlur(gray, (3, 3), 0)
            
            # Detección de bordes
            edges = cv2.Canny(blurred, 50, 150)
            
            # Encontrar contornos
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            buttons = []
            image_height, image_width = screenshot.shape[:2]
            
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                
                # Filtros para botones por detección de bordes
                if (70 <= w <= 250 and 25 <= h <= 60 and  # Tamaño típico de botón
                    w < image_width * 0.3 and h < image_height * 0.2 and  # No muy grande
                    2.5 <= w/h <= 6 and  # Relación aspecto de botón
                    x > 20 and y > 20 and  # No en bordes
                    x + w < image_width - 20 and y + h < image_height - 20):
                    
                    # Verificar que el contorno tenga forma rectangular
                    area = cv2.contourArea(contour)
                    rect_area = w * h
                    if rect_area > 0 and area / rect_area > 0.6:  # Al menos 60% rectangular
                        buttons.append({
                            'x': x,
                            'y': y, 
                            'width': w,
                            'height': h,
                            'type': 'button',
                            'color': 'edge_detected',
                            'area': w * h,
                            'aspect_ratio': w / h
                        })
            
            return buttons
            
        except Exception as e:
            print(f"Error en detección por bordes: {e}")
            return []
    
    def save_screenshot_with_annotations(self, elements, filename="annotated_screenshot.png"):
        """Guardar screenshot con elementos detectados marcados con mejor info"""
        screenshot = self.take_screenshot()
        if screenshot is None:
            return False
        
        img = Image.fromarray(screenshot)
        draw = ImageDraw.Draw(img)
        
        # Colores diferentes para diferentes tipos
        colors = {
            'blue': 'blue',
            'gray_light': 'gray', 
            'gray_medium': 'darkgray',
            'white': 'black',
            'edge_detected': 'green'
        }
        
        for i, element in enumerate(elements):
            x, y, w, h = element['x'], element['y'], element['width'], element['height']
            color_type = element.get('color', 'unknown')
            outline_color = colors.get(color_type, 'red')
            
            # Dibujar rectangulo alrededor del elemento con borde grueso
            draw.rectangle([x, y, x + w, y + h], outline=outline_color, width=4)
            
            # Dibujar punto central más grande
            center_x, center_y = x + w//2, y + h//2
            draw.ellipse([center_x-5, center_y-5, center_x+5, center_y+5], fill=outline_color)
            
            # Crear etiqueta grande y visible con V0, V1, etc.
            v_label = f"V{i}"
            info_label = f"{w}x{h} ({color_type})"
            
            # Fondo para la etiqueta V0, V1, etc. para mejor visibilidad
            label_y = y - 35 if y > 35 else y + h + 5
            
            # Dibujar fondo blanco para la etiqueta principal
            try:
                # Obtener tamaño aproximado del texto (estimado)
                text_width = len(v_label) * 12  # Aproximadamente 12px por caracter
                text_height = 16
                draw.rectangle([x-2, label_y-2, x + text_width + 2, label_y + text_height + 2], 
                              fill='white', outline=outline_color, width=2)
                
                # Texto principal V0, V1, etc. en negro sobre fondo blanco
                draw.text((x, label_y), v_label, fill='black')
                
                # Información adicional debajo en color del elemento
                info_y = label_y + 20 if y > 35 else label_y - 20
                draw.text((x, info_y), info_label, fill=outline_color)
                
            except:
                # Fallback simple si hay error
                draw.text((x, label_y), v_label, fill=outline_color)
                draw.text((x, label_y + 15), info_label, fill=outline_color)
        
        img.save(filename)
        print(f"Screenshot anotado guardado como: {filename}")
        return True

# Ejemplo de uso
if __name__ == "__main__":
    analyzer = ScreenshotAnalyzer()
    
    # Obtener info de ventana activa
    window_info = analyzer.get_active_window_info()
    if window_info:
        try:
            title = window_info['title'].encode('ascii', 'ignore').decode('ascii')
            print(f"Ventana activa: {title}")
        except:
            print("Ventana activa: [titulo con caracteres especiales]")
        print(f"Dimensiones: {window_info['width']}x{window_info['height']}")
    
    # Detectar elementos UI
    print("Detectando elementos de interfaz...")
    elements = analyzer.detect_ui_elements()
    print(f"Encontrados {len(elements)} elementos")
    
    # Guardar screenshot anotado
    if elements:
        analyzer.save_screenshot_with_annotations(elements)
    else:
        # Guardar screenshot simple si no hay elementos
        screenshot = analyzer.take_screenshot()
        if screenshot is not None:
            from PIL import Image
            img = Image.fromarray(screenshot)
            img.save("simple_screenshot.png")
            print("Screenshot simple guardado como: simple_screenshot.png")
    
    # Tomar screenshot simple
    screenshot = analyzer.take_screenshot()
    if screenshot is not None:
        print("Screenshot tomado exitosamente")
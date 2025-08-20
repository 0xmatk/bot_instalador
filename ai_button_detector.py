# -*- coding: utf-8 -*-
"""
Detector de botones inteligente para Windows 11
Usa múltiples métodos de IA y análisis para encontrar botones cuando fallan los métodos tradicionales
"""

import cv2
import numpy as np
from PIL import Image, ImageGrab
import pytesseract
import win32gui
import win32con
import win32api
import ctypes
from ctypes import wintypes
import time
import re
from collections import defaultdict

class AIButtonDetector:
    def __init__(self, debug=True):
        self.debug = debug
        self.detection_methods = [
            'edge_detection',
            'template_matching', 
            'color_clustering',
            'text_based_detection',
            'contour_analysis',
            'gradient_analysis'
        ]
        
    def capture_window_smart(self, hwnd=None):
        """Captura inteligente de ventana que funciona mejor en Windows 11"""
        methods = []
        
        # Método 1: Screenshot tradicional
        try:
            screenshot = np.array(ImageGrab.grab())
            screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
            methods.append(('traditional', screenshot))
        except:
            pass
            
        # Método 2: Captura de ventana específica
        if hwnd:
            try:
                # Obtener dimensiones de ventana
                rect = win32gui.GetWindowRect(hwnd)
                x, y, x2, y2 = rect
                width, height = x2 - x, y2 - y
                
                # Capturar solo esa región
                window_screenshot = np.array(ImageGrab.grab(bbox=(x, y, x2, y2)))
                window_screenshot = cv2.cvtColor(window_screenshot, cv2.COLOR_RGB2BGR)
                methods.append(('window_specific', window_screenshot, (x, y)))
            except:
                pass
        
        # Método 3: Captura con DPI awareness
        try:
            # Configurar DPI awareness temporalmente
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
            dpi_screenshot = np.array(ImageGrab.grab())
            dpi_screenshot = cv2.cvtColor(dpi_screenshot, cv2.COLOR_RGB2BGR)
            methods.append(('dpi_aware', dpi_screenshot))
        except:
            pass
            
        return methods
    
    def detect_buttons_ai(self, image, method='all'):
        """Detectar botones usando múltiples métodos de IA"""
        if method == 'all':
            all_buttons = []
            for detection_method in self.detection_methods:
                try:
                    buttons = getattr(self, f'_detect_{detection_method}')(image)
                    all_buttons.extend(buttons)
                except Exception as e:
                    if self.debug:
                        print(f"⚠️ Método {detection_method} falló: {e}")
            
            # Fusionar detecciones superpuestas
            return self._merge_overlapping_detections(all_buttons)
        else:
            return getattr(self, f'_detect_{method}')(image)
    
    def _detect_edge_detection(self, image):
        """Detectar botones por bordes"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Detectar bordes con múltiples parámetros
        edges1 = cv2.Canny(gray, 50, 150)
        edges2 = cv2.Canny(gray, 30, 100)
        edges3 = cv2.Canny(gray, 100, 200)
        
        buttons = []
        for i, edges in enumerate([edges1, edges2, edges3]):
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if 500 < area < 50000:  # Tamaño típico de botón
                    x, y, w, h = cv2.boundingRect(contour)
                    aspect_ratio = w / float(h)
                    
                    # Filtros para botones típicos
                    if (0.8 < aspect_ratio < 8.0 and  # Ratio típico de botón
                        w > 30 and h > 15):  # Tamaño mínimo
                        
                        confidence = 0.3 + (i * 0.1)  # Más confianza en edges más estrictos
                        buttons.append({
                            'method': 'edge_detection',
                            'bbox': (x, y, w, h),
                            'confidence': confidence,
                            'center': (x + w//2, y + h//2),
                            'area': area
                        })
        
        return buttons
    
    def _detect_template_matching(self, image):
        """Detectar botones por matching con templates comunes"""
        buttons = []
        
        # Templates comunes de botones (simplificados)
        templates = self._generate_button_templates()
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        for template_name, template in templates:
            try:
                result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
                locations = np.where(result >= 0.6)
                
                for pt in zip(*locations[::-1]):
                    x, y = pt
                    w, h = template.shape[:2]
                    buttons.append({
                        'method': 'template_matching',
                        'bbox': (x, y, w, h),
                        'confidence': 0.6,
                        'center': (x + w//2, y + h//2),
                        'template': template_name
                    })
            except:
                continue
                
        return buttons
    
    def _detect_color_clustering(self, image):
        """Detectar botones por clustering de colores"""
        buttons = []
        
        # Convertir a espacio de color más adecuado
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        
        # Buscar regiones con colores típicos de botones
        button_colors = [
            ([100, 110, 110], [140, 140, 140]),  # Gris claro (botones Windows)
            ([200, 220, 240], [255, 255, 255]),  # Casi blanco
            ([0, 100, 200], [50, 150, 255]),     # Azul (botones principales)
        ]
        
        for i, (lower, upper) in enumerate(button_colors):
            lower = np.array(lower)
            upper = np.array(upper)
            
            mask = cv2.inRange(image, lower, upper)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if 800 < area < 30000:
                    x, y, w, h = cv2.boundingRect(contour)
                    aspect_ratio = w / float(h)
                    
                    if 0.8 < aspect_ratio < 6.0 and w > 40 and h > 20:
                        buttons.append({
                            'method': 'color_clustering',
                            'bbox': (x, y, w, h),
                            'confidence': 0.4,
                            'center': (x + w//2, y + h//2),
                            'color_group': i
                        })
        
        return buttons
    
    def _detect_text_based_detection(self, image):
        """Detectar botones buscando texto típico de botones"""
        buttons = []
        
        # Palabras típicas de botones
        button_keywords = [
            'next', 'siguiente', 'continue', 'continuar',
            'install', 'instalar', 'setup', 'configurar',
            'accept', 'aceptar', 'agree', 'acepto',
            'ok', 'cancel', 'cancelar', 'finish', 'finalizar',
            'close', 'cerrar', 'yes', 'si', 'no'
        ]
        
        try:
            # OCR para encontrar texto
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Múltiples configuraciones de OCR
            configs = [
                '--psm 6',  # Uniform block of text
                '--psm 8',  # Single word
                '--psm 13', # Raw line
            ]
            
            for config in configs:
                try:
                    data = pytesseract.image_to_data(gray, config=config, output_type=pytesseract.Output.DICT)
                    
                    for i in range(len(data['text'])):
                        text = data['text'][i].lower().strip()
                        if text and any(keyword in text for keyword in button_keywords):
                            x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                            confidence = data['conf'][i] / 100.0
                            
                            if confidence > 0.3 and w > 20 and h > 10:
                                buttons.append({
                                    'method': 'text_based',
                                    'bbox': (x-10, y-5, w+20, h+10),  # Expandir área
                                    'confidence': confidence,
                                    'center': (x + w//2, y + h//2),
                                    'text': text
                                })
                except:
                    continue
                    
        except Exception as e:
            if self.debug:
                print(f"⚠️ OCR falló: {e}")
        
        return buttons
    
    def _detect_contour_analysis(self, image):
        """Detectar botones por análisis de contornos"""
        buttons = []
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Múltiples técnicas de procesamiento
        processed_images = [
            cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)[1],
            cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2),
            cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        ]
        
        for proc_img in processed_images:
            contours, _ = cv2.findContours(proc_img, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if 600 < area < 40000:
                    x, y, w, h = cv2.boundingRect(contour)
                    aspect_ratio = w / float(h)
                    
                    # Análisis de forma más detallado
                    hull = cv2.convexHull(contour)
                    hull_area = cv2.contourArea(hull)
                    solidity = float(area) / hull_area if hull_area > 0 else 0
                    
                    # Filtros para formas de botón
                    if (0.7 < aspect_ratio < 10.0 and 
                        w > 35 and h > 18 and
                        solidity > 0.8):  # Forma sólida, típica de botón
                        
                        buttons.append({
                            'method': 'contour_analysis',
                            'bbox': (x, y, w, h),
                            'confidence': 0.5,
                            'center': (x + w//2, y + h//2),
                            'solidity': solidity
                        })
        
        return buttons
    
    def _detect_gradient_analysis(self, image):
        """Detectar botones por análisis de gradientes"""
        buttons = []
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Calcular gradientes
        grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        magnitude = np.sqrt(grad_x**2 + grad_y**2)
        
        # Normalizar
        magnitude = np.uint8(255 * magnitude / np.max(magnitude))
        
        # Encontrar regiones con gradientes fuertes (bordes de botón)
        _, thresh = cv2.threshold(magnitude, 50, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if 700 < area < 35000:
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / float(h)
                
                if 0.8 < aspect_ratio < 8.0 and w > 30 and h > 15:
                    buttons.append({
                        'method': 'gradient_analysis',
                        'bbox': (x, y, w, h),
                        'confidence': 0.4,
                        'center': (x + w//2, y + h//2),
                        'gradient_strength': np.mean(magnitude[y:y+h, x:x+w])
                    })
        
        return buttons
    
    def _generate_button_templates(self):
        """Generar templates simples de botones"""
        templates = []
        
        # Template de botón rectangular simple
        for w, h in [(80, 25), (100, 30), (120, 35), (60, 20)]:
            template = np.zeros((h, w), dtype=np.uint8)
            cv2.rectangle(template, (2, 2), (w-3, h-3), 255, 1)
            templates.append((f'rect_{w}x{h}', template))
        
        # Template de botón con relleno
        for w, h in [(90, 28), (110, 32)]:
            template = np.full((h, w), 128, dtype=np.uint8)
            cv2.rectangle(template, (0, 0), (w-1, h-1), 255, 2)
            templates.append((f'filled_{w}x{h}', template))
        
        return templates
    
    def _merge_overlapping_detections(self, buttons):
        """Fusionar detecciones superpuestas"""
        if not buttons:
            return []
        
        # Agrupar por posición similar
        merged = []
        used = set()
        
        for i, button1 in enumerate(buttons):
            if i in used:
                continue
                
            group = [button1]
            x1, y1, w1, h1 = button1['bbox']
            
            for j, button2 in enumerate(buttons[i+1:], i+1):
                if j in used:
                    continue
                    
                x2, y2, w2, h2 = button2['bbox']
                
                # Calcular overlap
                overlap_x = max(0, min(x1+w1, x2+w2) - max(x1, x2))
                overlap_y = max(0, min(y1+h1, y2+h2) - max(y1, y2))
                overlap_area = overlap_x * overlap_y
                
                area1 = w1 * h1
                area2 = w2 * h2
                min_area = min(area1, area2)
                
                # Si hay overlap significativo, agrupar
                if overlap_area / min_area > 0.3:
                    group.append(button2)
                    used.add(j)
            
            # Crear detección fusionada
            if group:
                # Promediar posiciones y tomar la mejor confianza
                avg_x = int(np.mean([b['bbox'][0] for b in group]))
                avg_y = int(np.mean([b['bbox'][1] for b in group]))
                avg_w = int(np.mean([b['bbox'][2] for b in group]))
                avg_h = int(np.mean([b['bbox'][3] for b in group]))
                
                max_confidence = max([b['confidence'] for b in group])
                methods = [b['method'] for b in group]
                
                merged.append({
                    'method': '+'.join(set(methods)),
                    'bbox': (avg_x, avg_y, avg_w, avg_h),
                    'confidence': max_confidence,
                    'center': (avg_x + avg_w//2, avg_y + avg_h//2),
                    'detection_count': len(group)
                })
            
            used.add(i)
        
        # Ordenar por confianza
        return sorted(merged, key=lambda x: x['confidence'], reverse=True)
    
    def find_best_buttons(self, hwnd=None, min_confidence=0.3):
        """Encontrar los mejores candidatos a botones"""
        print("🔍 === ANÁLISIS INTELIGENTE DE BOTONES ===")
        
        # Capturar con múltiples métodos
        capture_methods = self.capture_window_smart(hwnd)
        
        all_detections = []
        
        for method_name, image, *offset in capture_methods:
            print(f"📸 Analizando captura: {method_name}")
            
            if image is not None and image.size > 0:
                buttons = self.detect_buttons_ai(image)
                
                # Ajustar coordenadas si hay offset
                if offset:
                    offset_x, offset_y = offset[0]
                    for button in buttons:
                        x, y, w, h = button['bbox']
                        button['bbox'] = (x + offset_x, y + offset_y, w, h)
                        button['center'] = (x + offset_x + w//2, y + offset_y + h//2)
                
                print(f"   🎯 Encontrados {len(buttons)} candidatos")
                all_detections.extend(buttons)
        
        # Fusionar todas las detecciones
        final_buttons = self._merge_overlapping_detections(all_detections)
        
        # Filtrar por confianza mínima
        good_buttons = [b for b in final_buttons if b['confidence'] >= min_confidence]
        
        print(f"✅ Total de botones finales: {len(good_buttons)}")
        
        return good_buttons
    
    def detect_buttons(self, save_screenshot=True, filename="button_detection.png"):
        """
        Método principal para detectar botones y opcionalmente guardar screenshot marcado
        """
        print("🔍 Detectando botones en pantalla...")
        
        # Detectar botones usando todos los métodos disponibles
        buttons = self.find_best_buttons()
        
        if save_screenshot and buttons:
            self.save_detection_debug(buttons, filename)
            print(f"📸 Screenshot guardado: {filename}")
        
        # Convertir formato para compatibilidad con ui_clicker
        formatted_buttons = []
        for i, button in enumerate(buttons):
            x, y, w, h = button['bbox']
            formatted_button = {
                'x': x,
                'y': y,
                'width': w,
                'height': h,
                'confidence': button['confidence'],
                'method': button['method'],
                'text': button.get('text', f'Button_{i+1}'),
                'center_x': button['center'][0],
                'center_y': button['center'][1]
            }
            formatted_buttons.append(formatted_button)
        
        print(f"✅ Detectados {len(formatted_buttons)} botones")
        return formatted_buttons

    def save_detection_debug(self, buttons, filename="ai_detection_debug.png"):
        """Guardar imagen con detecciones para debug"""
        try:
            screenshot = np.array(ImageGrab.grab())
            screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
            
            colors = [(0, 255, 0), (255, 0, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255)]
            
            for i, button in enumerate(buttons):
                x, y, w, h = button['bbox']
                color = colors[i % len(colors)]
                
                # Dibujar rectángulo
                cv2.rectangle(screenshot, (x, y), (x+w, y+h), color, 2)
                
                # Dibujar información
                info = f"AI{i+1}: {button['method'][:10]} ({button['confidence']:.2f})"
                cv2.putText(screenshot, info, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                
                # Dibujar centro
                cx, cy = button['center']
                cv2.circle(screenshot, (cx, cy), 3, color, -1)
                
                # Agregar texto del botón si existe
                if 'text' in button and button['text']:
                    text_info = f"Text: {button['text'][:15]}"
                    cv2.putText(screenshot, text_info, (x, y+h+15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            
            cv2.imwrite(filename, screenshot)
            print(f"🖼️ Debug guardado en: {filename}")
            return filename
            
        except Exception as e:
            print(f"❌ Error guardando debug: {e}")
            return None
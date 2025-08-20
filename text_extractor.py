# -*- coding: utf-8 -*-
import cv2
import numpy as np
import pytesseract
import pyautogui
from PIL import Image, ImageEnhance, ImageFilter
import re
import win32gui
import win32con

class TextExtractor:
    def __init__(self, tesseract_path=None):
        # Configurar ruta de Tesseract si es necesario
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        
        # Configurar pyautogui
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.5
    
    def take_screenshot(self, region=None):
        """Tomar captura de pantalla"""
        try:
            screenshot = pyautogui.screenshot(region=region)
            return np.array(screenshot)
        except Exception as e:
            print(f"Error tomando screenshot: {e}")
            return None
    
    def preprocess_image_for_ocr(self, image):
        """Preprocesar imagen para mejorar OCR"""
        # Convertir a PIL Image si es numpy array
        if isinstance(image, np.ndarray):
            pil_image = Image.fromarray(image)
        else:
            pil_image = image
        
        # Convertir a escala de grises
        gray_image = pil_image.convert('L')
        
        # Mejorar contraste
        enhancer = ImageEnhance.Contrast(gray_image)
        contrast_image = enhancer.enhance(2.0)
        
        # Aumentar brillo
        enhancer = ImageEnhance.Brightness(contrast_image)
        bright_image = enhancer.enhance(1.2)
        
        # Aplicar filtro de suavizado
        smooth_image = bright_image.filter(ImageFilter.MedianFilter())
        
        return smooth_image
    
    def extract_text_from_image(self, image, config='--psm 6'):
        """Extraer texto de imagen usando OCR"""
        try:
            processed_image = self.preprocess_image_for_ocr(image)
            text = pytesseract.image_to_string(processed_image, config=config, lang='eng+spa')
            return text.strip()
        except Exception as e:
            print(f"Error en OCR: {e}")
            return ""
    
    def extract_text_from_screen(self, region=None):
        """Extraer texto de la pantalla"""
        screenshot = self.take_screenshot(region)
        if screenshot is None:
            return ""
        
        return self.extract_text_from_image(screenshot)
    
    def find_text_regions(self, image):
        """Encontrar regiones que contienen texto"""
        # Convertir a escala de grises
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        
        # Aplicar threshold
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Encontrar contornos
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        text_regions = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # Filtrar por tamaño (probable texto)
            if w > 30 and h > 10 and w < 800 and h < 100:
                # Extraer región de texto
                text_region = image[y:y+h, x:x+w]
                text = self.extract_text_from_image(text_region)
                
                if text.strip():  # Solo si hay texto
                    text_regions.append({
                        'x': x, 'y': y, 'width': w, 'height': h,
                        'text': text.strip()
                    })
        
        return text_regions
    
    def find_buttons_with_text(self, target_texts):
        """Buscar botones que contengan textos específicos"""
        screenshot = self.take_screenshot()
        if screenshot is None:
            return []
        
        text_regions = self.find_text_regions(screenshot)
        matching_buttons = []
        
        # Normalizar textos objetivo
        target_texts_lower = [text.lower() for text in target_texts]
        
        for region in text_regions:
            text_lower = region['text'].lower()
            
            # Buscar coincidencias
            for target in target_texts_lower:
                if target in text_lower or any(word in text_lower for word in target.split()):
                    region['matched_text'] = target
                    matching_buttons.append(region)
                    break
        
        return matching_buttons
    
    def extract_window_text(self):
        """Extraer todo el texto de la ventana activa"""
        try:
            hwnd = win32gui.GetForegroundWindow()
            window_rect = win32gui.GetWindowRect(hwnd)
            
            # Tomar screenshot solo de la ventana
            region = (window_rect[0], window_rect[1], 
                     window_rect[2] - window_rect[0], 
                     window_rect[3] - window_rect[1])
            
            text = self.extract_text_from_screen(region)
            return text
        except Exception as e:
            print(f"Error extrayendo texto de ventana: {e}")
            return ""
    
    def find_installation_elements(self):
        """Buscar elementos típicos de instaladores"""
        common_texts = [
            'next', 'siguiente', 'continuar', 'continue',
            'install', 'instalar', 'setup', 'configurar',
            'cancel', 'cancelar', 'back', 'atras', 'volver',
            'accept', 'aceptar', 'agree', 'acepto',
            'finish', 'finalizar', 'complete', 'completar',
            'browse', 'examinar', 'change', 'cambiar',
            'yes', 'si', 'no', 'ok', 'close', 'cerrar'
        ]
        
        return self.find_buttons_with_text(common_texts)
    
    def get_installation_progress(self):
        """Detectar progreso de instalación"""
        text = self.extract_window_text()
        
        # Patrones para detectar progreso
        progress_patterns = [
            r'(\d+)%',  # Porcentajes
            r'(\d+)/(\d+)',  # Progreso tipo "5/10"
            r'installing|instalando',  # Palabras de instalación
            r'copying|copiando',  # Copiando archivos
            r'extracting|extrayendo',  # Extrayendo
            r'configuring|configurando'  # Configurando
        ]
        
        progress_info = {
            'percentage': None,
            'status': 'unknown',
            'is_installing': False
        }
        
        for pattern in progress_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                if pattern == r'(\d+)%':
                    progress_info['percentage'] = int(matches[0])
                elif 'install' in pattern.lower():
                    progress_info['is_installing'] = True
                    progress_info['status'] = 'installing'
                elif any(word in pattern.lower() for word in ['copy', 'extract', 'config']):
                    progress_info['is_installing'] = True
                    progress_info['status'] = matches[0] if matches else 'processing'
        
        return progress_info

# Ejemplo de uso
if __name__ == "__main__":
    # Nota: Necesitas instalar Tesseract OCR
    extractor = TextExtractor()
    
    print("=== Extrayendo texto de la ventana ===")
    window_text = extractor.extract_window_text()
    print(f"Texto encontrado:\n{window_text[:500]}...")  # Primeros 500 caracteres
    
    print("\n=== Buscando elementos de instalación ===")
    installation_elements = extractor.find_installation_elements()
    print(f"Encontrados {len(installation_elements)} elementos:")
    
    for element in installation_elements:
        print(f"- Texto: '{element['text']}' en posición ({element['x']}, {element['y']})")
    
    print("\n=== Verificando progreso de instalación ===")
    progress = extractor.get_installation_progress()
    print(f"Estado: {progress['status']}")
    print(f"Instalando: {progress['is_installing']}")
    if progress['percentage']:
        print(f"Progreso: {progress['percentage']}%")
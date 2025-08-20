# -*- coding: utf-8 -*-
import pyautogui
import win32gui
import win32con
import win32api
import time
import ctypes
import sys
import os
import cv2
import numpy as np
from PIL import Image, ImageGrab
import pytesseract
from text_extractor_simple import SimpleTextExtractor
from screenshot_analyzer import ScreenshotAnalyzer
from ai_button_detector import AIButtonDetector

class UIClicker:
    def __init__(self):
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 1.0
        
        self.text_extractor = SimpleTextExtractor()
        self.screenshot_analyzer = ScreenshotAnalyzer()
        self.ai_detector = AIButtonDetector()
        
        self.setup_dpi_awareness()
    
    def setup_dpi_awareness(self):
        """Configurar DPI awareness para mejor precisión de clicks"""
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except:
            pass
    
    def is_admin(self):
        """Verificar si el script tiene permisos de administrador"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    
    def restart_as_admin(self):
        """Reiniciar el script con permisos de administrador"""
        try:
            if self.is_admin():
                return True
            
            print("Reiniciando con permisos de administrador...")
            ctypes.windll.shell32.ShellExecuteW(
                None, 
                "runas", 
                sys.executable, 
                " ".join(sys.argv), 
                None, 
                1
            )
            return True
        except Exception as e:
            print(f"Error al reiniciar como admin: {e}")
            return False
    
    def click_at_coordinates(self, x, y, button='left', clicks=1):
        """Click en coordenadas específicas"""
        try:
            if button == 'left':
                pyautogui.click(x, y, clicks=clicks, button='left')
            elif button == 'right':
                pyautogui.click(x, y, clicks=clicks, button='right')
            else:
                pyautogui.click(x, y, clicks=clicks)
            
            time.sleep(0.5)
            return True
        except Exception as e:
            print(f"Error en click: {e}")
            return False
    
    def find_button_by_text(self, button_text, window_hwnd=None):
        """Encontrar botón por texto usando Win32 API"""
        try:
            if window_hwnd is None:
                window_hwnd = win32gui.GetForegroundWindow()
            
            def enum_child_windows(hwnd, results):
                try:
                    window_text = win32gui.GetWindowText(hwnd).lower()
                    class_name = win32gui.GetClassName(hwnd).lower()
                    
                    if 'button' in class_name and button_text.lower() in window_text:
                        results.append(hwnd)
                except:
                    pass
                return True
            
            results = []
            win32gui.EnumChildWindows(window_hwnd, enum_child_windows, results)
            return results[0] if results else None
            
        except Exception:
            return None
    
    def click_control_by_handle(self, hwnd):
        """Click en control usando su handle"""
        try:
            rect = win32gui.GetWindowRect(hwnd)
            x = (rect[0] + rect[2]) // 2
            y = (rect[1] + rect[3]) // 2
            
            return self.click_at_coordinates(x, y)
        except Exception:
            return False
    
    def send_button_message(self, hwnd):
        """Enviar mensaje BN_CLICKED al botón"""
        try:
            win32api.SendMessage(hwnd, win32con.BM_CLICK, 0, 0)
            time.sleep(0.5)
            return True
        except Exception:
            return False
    
    def find_button_by_visual_analysis(self, button_texts, save_screenshot=False):
        """Encontrar botón usando análisis visual con opción de screenshot"""
        try:
            # Usar el nuevo método detect_buttons que incluye screenshot automático
            ai_buttons = self.ai_detector.detect_buttons(save_screenshot=save_screenshot)
            if not ai_buttons:
                return None
            
            # Buscar botón que coincida con el texto
            for button in ai_buttons:
                for text in button_texts:
                    if text.lower() in str(button.get('text', '')).lower():
                        return {'x': button['center_x'], 'y': button['center_y']}
            
            # Si no hay coincidencia por texto, usar el primer botón detectado
            if ai_buttons:
                return {'x': ai_buttons[0]['center_x'], 'y': ai_buttons[0]['center_y']}
            
            return None
            
        except Exception as e:
            print(f"Error en análisis visual: {e}")
            return None
    
    def click_button_by_text(self, button_text, save_screenshot=False):
        """Click en botón por texto priorizando análisis visual con opción de screenshot"""
        # Método 1: Análisis visual (prioritario para Windows 11)
        button_variations = [button_text]
        if button_text == 'next':
            button_variations.extend(['continue', 'continuar', 'siguiente'])
        elif button_text == 'install':
            button_variations.extend(['instalar', 'setup'])
        elif button_text == 'accept':
            button_variations.extend(['aceptar', 'ok', 'yes'])
        elif button_text == 'finish':
            button_variations.extend(['finalizar', 'close', 'cerrar'])
        
        visual_button = self.find_button_by_visual_analysis(button_variations, save_screenshot)
        if visual_button:
            return self.click_at_coordinates(visual_button['x'], visual_button['y'])
        
        # Método 2: Win32 API (fallback para aplicaciones legacy)
        print("Análisis visual falló, intentando Win32 API...")
        button_hwnd = self.find_button_by_text(button_text)
        if button_hwnd:
            if self.send_button_message(button_hwnd):
                return True
            return self.click_control_by_handle(button_hwnd)
        
        return False
    
    def click_next_button(self):
        """Click en botón Next/Siguiente/Continue"""
        variations = ['continue', 'continuar', 'next', 'siguiente']
        for variation in variations:
            if self.click_button_by_text(variation):
                return True
        return False
    
    def click_install_button(self):
        """Click en botón Install/Instalar"""
        variations = ['install', 'instalar', 'setup']
        for variation in variations:
            if self.click_button_by_text(variation):
                return True
        return False
    
    def click_accept_button(self):
        """Click en botón Accept/Aceptar"""
        variations = ['accept', 'aceptar', 'ok', 'yes']
        for variation in variations:
            if self.click_button_by_text(variation):
                return True
        return False
    
    def click_finish_button(self):
        """Click en botón Finish/Finalizar"""
        variations = ['finish', 'finalizar', 'close', 'cerrar']
        for variation in variations:
            if self.click_button_by_text(variation):
                return True
        return False
    
    def detect_progress_bar(self):
        """Detectar barras de progreso en pantalla"""
        try:
            screenshot = np.array(ImageGrab.grab())
            gray = cv2.cvtColor(screenshot, cv2.COLOR_RGB2GRAY)
            
            # Buscar patrones típicos de barras de progreso
            progress_bars = []
            
            # Método 1: Detectar rectángulos largos y estrechos
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / float(h) if h > 0 else 0
                
                # Barras de progreso típicas: largas y estrechas
                if (aspect_ratio > 5 and w > 100 and 10 < h < 50):
                    # Analizar contenido para ver si parece barra de progreso
                    roi = gray[y:y+h, x:x+w]
                    if roi.size > 0:
                        # Buscar gradientes horizontales típicos de barras
                        grad_x = cv2.Sobel(roi, cv2.CV_64F, 1, 0, ksize=3)
                        gradient_strength = np.mean(np.abs(grad_x))
                        
                        if gradient_strength > 10:  # Umbral para detectar transición
                            progress_bars.append({
                                'x': x, 'y': y, 'width': w, 'height': h,
                                'gradient_strength': gradient_strength
                            })
            
            # Analizar la mejor barra de progreso encontrada
            if progress_bars:
                best_bar = max(progress_bars, key=lambda x: x['gradient_strength'])
                
                # Estimar progreso analizando la barra
                progress_value = self._estimate_progress_value(gray, best_bar)
                
                return {
                    'found': True,
                    'is_active': progress_value > 0 and progress_value < 100,
                    'progress': progress_value,
                    'position': best_bar
                }
            
            return {'found': False, 'is_active': False, 'progress': 0}
            
        except Exception as e:
            print(f"Error detectando barra de progreso: {e}")
            return {'found': False, 'is_active': False, 'progress': 0}
    
    def _estimate_progress_value(self, gray_image, progress_bar):
        """Estimar el valor de progreso de una barra"""
        try:
            x, y, w, h = progress_bar['x'], progress_bar['y'], progress_bar['width'], progress_bar['height']
            roi = gray_image[y:y+h, x:x+w]
            
            if roi.size == 0:
                return 0
            
            # Analizar intensidad horizontal para encontrar la división
            horizontal_profile = np.mean(roi, axis=0)
            
            # Buscar cambio significativo en intensidad
            gradient = np.gradient(horizontal_profile)
            significant_changes = np.where(np.abs(gradient) > np.std(gradient) * 2)[0]
            
            if len(significant_changes) > 0:
                # El último cambio significativo indica el final del progreso
                progress_end = significant_changes[-1]
                progress_percentage = (progress_end / w) * 100
                return min(100, max(0, progress_percentage))
            
            return 0
            
        except Exception as e:
            print(f"Error estimando progreso: {e}")
            return 0
    
    def wait_for_progress_completion(self, max_wait_time=300, check_interval=2):
        """Esperar a que se complete la barra de progreso"""
        print("⏳ Esperando finalización del progreso...")
        start_time = time.time()
        last_progress = 0
        stuck_count = 0
        
        while time.time() - start_time < max_wait_time:
            progress_info = self.detect_progress_bar()
            
            if progress_info['found']:
                current_progress = progress_info['progress']
                print(f"📊 Progreso: {current_progress:.1f}%")
                
                # Si el progreso llegó al 100%, esperar un poco más y verificar
                if current_progress >= 99:
                    time.sleep(3)
                    # Verificar si cambió el estado de la ventana
                    new_state = self.detect_installation_state()
                    if new_state in ['finished', 'waiting']:
                        print("✅ Progreso completado")
                        return True
                
                # Detectar si el progreso está atascado
                if abs(current_progress - last_progress) < 1:
                    stuck_count += 1
                    if stuck_count > 10:  # 20 segundos sin cambio
                        print("⚠️ Progreso parece atascado, continuando...")
                        return False
                else:
                    stuck_count = 0
                    last_progress = current_progress
            else:
                # No hay barra de progreso visible, verificar estado
                state = self.detect_installation_state()
                if state in ['finished', 'waiting', 'ready_to_install']:
                    print("✅ Proceso completado (sin barra visible)")
                    return True
            
            time.sleep(check_interval)
        
        print("⚠️ Timeout esperando progreso")
        return False
    
    def generate_button_diagnostic(self, filename="button_diagnostic.png"):
        """Generar un diagnóstico completo de botones con screenshot marcado"""
        print("\n🔧 === DIAGNÓSTICO DE BOTONES ===")
        try:
            buttons = self.ai_detector.detect_buttons(save_screenshot=True, filename=filename)
            
            if not buttons:
                print("❌ No se encontraron botones")
                return False
            
            print(f"✅ Encontrados {len(buttons)} botones:")
            for i, button in enumerate(buttons, 1):
                print(f"   {i}. Posición: ({button['x']}, {button['y']}) - "
                      f"Tamaño: {button['width']}x{button['height']} - "
                      f"Confianza: {button['confidence']:.2f} - "
                      f"Método: {button['method']} - "
                      f"Texto: {button.get('text', 'N/A')}")
            
            # Agregar información de barra de progreso
            progress_info = self.detect_progress_bar()
            if progress_info['found']:
                print(f"\n📊 Barra de progreso detectada:")
                print(f"   Progreso: {progress_info['progress']:.1f}%")
                print(f"   Activa: {progress_info['is_active']}")
            
            print(f"📸 Screenshot guardado en: {filename}")
            return True
            
        except Exception as e:
            print(f"❌ Error generando diagnóstico: {e}")
            return False

    def detect_installation_state(self):
        """Detectar el estado actual de la instalación con análisis avanzado"""
        try:
            # Método 1: Análisis de botones disponibles (más confiable en Win11)
            ai_buttons = self.ai_detector.detect_buttons(save_screenshot=False)
            button_analysis = self._analyze_available_buttons(ai_buttons)
            
            # Método 2: Detección de barras de progreso
            progress_info = self.detect_progress_bar()
            
            # Método 3: Análisis de texto en pantalla
            screen_text = self._analyze_screen_text()
            
            # Combinar toda la información para determinar el estado
            return self._determine_state_from_analysis(button_analysis, progress_info, screen_text)
            
        except Exception as e:
            print(f"Error detectando estado: {e}")
            return 'unknown'
    
    def _analyze_available_buttons(self, ai_buttons):
        """Analizar los botones disponibles y su significado"""
        button_info = {
            'finish_buttons': [],
            'install_buttons': [],
            'next_buttons': [],
            'cancel_buttons': [],
            'other_buttons': []
        }
        
        if ai_buttons:
            for button in ai_buttons:
                button_text = str(button.get('text', '')).lower()
                
                if any(word in button_text for word in ['finish', 'close', 'done', 'finalizar', 'cerrar', 'terminar']):
                    button_info['finish_buttons'].append(button)
                elif any(word in button_text for word in ['install', 'instalar', 'setup']):
                    button_info['install_buttons'].append(button)
                elif any(word in button_text for word in ['next', 'continue', 'siguiente', 'continuar']):
                    button_info['next_buttons'].append(button)
                elif any(word in button_text for word in ['cancel', 'cancelar', 'exit', 'salir']):
                    button_info['cancel_buttons'].append(button)
                else:
                    button_info['other_buttons'].append(button)
        
        return button_info
    
    def _analyze_screen_text(self):
        """Analizar texto en pantalla usando OCR avanzado"""
        try:
            screenshot = np.array(ImageGrab.grab())
            gray = cv2.cvtColor(screenshot, cv2.COLOR_RGB2GRAY)
            
            # OCR para detectar texto relevante
            text_data = pytesseract.image_to_string(gray, config='--psm 6').lower()
            
            analysis = {
                'installing': any(word in text_data for word in ['installing', 'instalando', 'copying', 'copiando', 'extracting']),
                'complete': any(word in text_data for word in ['complete', 'completado', 'finished', 'successful', 'exitoso']),
                'error': any(word in text_data for word in ['error', 'failed', 'falló', 'problema', 'warning']),
                'progress': any(word in text_data for word in ['progress', 'progreso', '%', 'percent']),
                'waiting': any(word in text_data for word in ['waiting', 'esperando', 'please wait', 'por favor espere'])
            }
            
            return analysis
            
        except Exception as e:
            print(f"Error analizando texto: {e}")
            return {}
    
    def _determine_state_from_analysis(self, button_analysis, progress_info, screen_text):
        """Determinar el estado basado en todo el análisis"""
        # Prioridad 1: Si hay barra de progreso activa, está instalando
        if progress_info and progress_info.get('is_active', False):
            progress_value = progress_info.get('progress', 0)
            if progress_value >= 100:
                return 'finished'
            else:
                return 'installing'
        
        # Prioridad 2: Análisis de texto de error
        if screen_text.get('error', False):
            return 'error'
        
        # Prioridad 3: Texto que indica instalación completa
        if screen_text.get('complete', False) or button_analysis.get('finish_buttons'):
            return 'finished'
        
        # Prioridad 4: Texto que indica instalación en progreso
        if screen_text.get('installing', False) or screen_text.get('progress', False):
            return 'installing'
        
        # Prioridad 5: Botones disponibles
        if button_analysis.get('install_buttons'):
            return 'ready_to_install'
        elif button_analysis.get('next_buttons'):
            return 'waiting'
        
        return 'waiting'
    
    def auto_install(self, max_steps=20):
        """Instalación automática inteligente con análisis avanzado"""
        print("🚀 Iniciando instalación automática inteligente...")
        
        for step in range(max_steps):
            print(f"\n--- Paso {step + 1}/{max_steps} ---")
            
            state = self.detect_installation_state()
            print(f"🔍 Estado detectado: {state}")
            
            # Manejo inteligente de estados
            if state == 'installing':
                print("⏳ Instalación en progreso, esperando con monitoreo...")
                if self.wait_for_progress_completion():
                    print("✅ Progreso completado, continuando...")
                    continue
                else:
                    print("⚠️ Progreso tomó demasiado tiempo, verificando estado...")
                    time.sleep(3)
                    continue
                    
            elif state == 'finished':
                print("🎉 Instalación completada")
                if self.click_finish_button():
                    print("✅ Instalación finalizada exitosamente")
                    return True
                else:
                    print("⚠️ No se pudo hacer click en Finish, intentando cerrar...")
                    if self.click_button_by_text('close', save_screenshot=True):
                        return True
                break
                
            elif state == 'error':
                print("❌ Error detectado en la instalación")
                self.generate_button_diagnostic(f"error_step_{step+1}_diagnostic.png")
                break
                
            elif state == 'ready_to_install':
                print("📦 Listo para instalar")
                if self.click_install_button():
                    print("🔨 Botón Install clickeado, esperando inicio...")
                    time.sleep(3)
                    continue
            
            # Intentar avanzar según prioridades
            actions_tried = []
            
            # Prioridad 1: Aceptar términos si es necesario
            if self.click_button_by_text('accept', save_screenshot=True):
                print("📝 Términos aceptados")
                actions_tried.append('accept')
                time.sleep(2)
                continue
            
            # Prioridad 2: Continuar/Next
            if self.click_button_by_text('next', save_screenshot=True):
                print("▶️ Avanzando al siguiente paso")
                actions_tried.append('next')
                time.sleep(2)
                continue
            
            # Prioridad 3: Instalar
            if self.click_button_by_text('install', save_screenshot=True):
                print("🔨 Iniciando instalación")
                actions_tried.append('install')
                time.sleep(3)
                continue
            
            # Prioridad 4: Intentar con variaciones de continue
            if self.click_button_by_text('continue', save_screenshot=True):
                print("▶️ Continuando proceso")
                actions_tried.append('continue')
                time.sleep(2)
                continue
            
            # Si no se pudo hacer nada, generar diagnóstico
            print("⚠️ No se encontraron acciones válidas")
            print(f"🔍 Acciones intentadas: {actions_tried}")
            print("📸 Generando diagnóstico avanzado...")
            
            self.generate_button_diagnostic(f"install_step_{step+1}_diagnostic.png")
            
            # Dar una oportunidad más esperando un poco
            print("⏳ Esperando 5 segundos por si hay cambios...")
            time.sleep(5)
            
            # Verificar si cambió el estado
            new_state = self.detect_installation_state()
            if new_state != state:
                print(f"🔄 Estado cambió de {state} a {new_state}, continuando...")
                continue
            else:
                print("❌ Sin cambios detectados, finalizando...")
                break
        
        print("🏁 Instalación automática finalizada")
        return False
    
    def is_installation_complete(self):
        """Verificar si la instalación está completamente terminada"""
        try:
            # Método 1: Verificar si hay ventanas típicas de instalación activas
            def enum_windows(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    window_title = win32gui.GetWindowText(hwnd).lower()
                    class_name = win32gui.GetClassName(hwnd).lower()
                    
                    # Palabras clave que indican instaladores
                    installer_keywords = ['setup', 'install', 'wizard', 'installer']
                    completion_keywords = ['complete', 'finish', 'done', 'success']
                    
                    if any(keyword in window_title for keyword in installer_keywords):
                        windows.append({
                            'hwnd': hwnd,
                            'title': window_title,
                            'class': class_name,
                            'is_completion': any(word in window_title for word in completion_keywords)
                        })
                return True
            
            windows = []
            win32gui.EnumWindows(enum_windows, windows)
            
            # Método 2: Análisis de botones y estado actual
            state = self.detect_installation_state()
            button_analysis = self._analyze_available_buttons(
                self.ai_detector.detect_buttons(save_screenshot=False)
            )
            
            # Criterios para determinar finalización completa
            has_completion_window = any(w['is_completion'] for w in windows)
            has_finish_buttons = len(button_analysis.get('finish_buttons', [])) > 0
            state_indicates_complete = state in ['finished']
            
            # Verificar si quedan procesos de instalación activos
            no_active_installers = len([w for w in windows if not w['is_completion']]) == 0
            
            completion_score = sum([
                has_completion_window * 3,
                has_finish_buttons * 2,
                state_indicates_complete * 2,
                no_active_installers * 1
            ])
            
            return {
                'is_complete': completion_score >= 4,
                'confidence': min(100, completion_score * 12.5),
                'indicators': {
                    'completion_window': has_completion_window,
                    'finish_buttons': has_finish_buttons,
                    'state_complete': state_indicates_complete,
                    'no_active_installers': no_active_installers
                },
                'active_windows': windows
            }
            
        except Exception as e:
            print(f"Error verificando finalización: {e}")
            return {'is_complete': False, 'confidence': 0, 'indicators': {}}
    
    def smart_completion_handler(self):
        """Manejo inteligente de la finalización de instalación"""
        print("🎯 Iniciando manejo inteligente de finalización...")
        
        max_attempts = 5
        for attempt in range(max_attempts):
            print(f"\n--- Intento {attempt + 1}/{max_attempts} ---")
            
            completion_info = self.is_installation_complete()
            print(f"🔍 Confianza de finalización: {completion_info['confidence']:.1f}%")
            
            if completion_info['is_complete']:
                print("✅ Instalación detectada como completa")
                
                # Intentar cerrar ventanas de finalización
                if self.click_finish_button():
                    print("🎉 Finalización exitosa")
                    return True
                elif self.click_button_by_text('close'):
                    print("🎉 Ventana cerrada exitosamente")
                    return True
                elif self.click_button_by_text('ok'):
                    print("🎉 Confirmación exitosa")
                    return True
                else:
                    print("⚠️ No se pudo cerrar automáticamente")
                    return True  # Considerar exitoso de cualquier manera
            else:
                print("⏳ Instalación aún no completa, esperando...")
                time.sleep(3)
        
        print("⚠️ No se pudo confirmar finalización completa")
        return False

if __name__ == "__main__":
    clicker = UIClicker()
    
    # Verificar permisos de administrador y reiniciar si es necesario
    if not clicker.is_admin():
        print("ADVERTENCIA: El script no tiene permisos de administrador.")
        print("Muchos instaladores requieren permisos elevados para funcionar correctamente.")
        restart = input("¿Reiniciar como administrador? (s/n): ").lower().strip()
        
        if restart == 's':
            if clicker.restart_as_admin():
                print("Reiniciando...")
                sys.exit(0)
            else:
                print("Error al reiniciar. Continuando sin permisos de admin...")
        else:
            print("Continuando sin permisos de administrador...")
            print("NOTA: Algunos instaladores pueden fallar sin permisos elevados.")
    
    print("\n=== INSTALADOR AUTOMÁTICO INTELIGENTE ===")
    print("1 - Instalación automática inteligente")
    print("2 - Click Next")
    print("3 - Click Install") 
    print("4 - Click Accept")
    print("5 - Click Finish")
    print("6 - Diagnóstico de botones (con screenshot)")
    print("7 - Detectar estado de instalación")
    print("8 - Detectar barra de progreso")
    print("9 - Esperar finalización de progreso")
    print("A - Manejo inteligente de finalización")
    print("0 - Salir")
    
    while True:
        try:
            command = input("\nComando: ").strip()
            
            if command == '0':
                break
            elif command == '1':
                clicker.auto_install()
            elif command == '2':
                clicker.click_next_button()
            elif command == '3':
                clicker.click_install_button()
            elif command == '4':
                clicker.click_accept_button()
            elif command == '5':
                clicker.click_finish_button()
            elif command == '6':
                clicker.generate_button_diagnostic()
            elif command == '7':
                state = clicker.detect_installation_state()
                print(f"🔍 Estado actual: {state}")
            elif command == '8':
                progress_info = clicker.detect_progress_bar()
                if progress_info['found']:
                    print(f"📊 Barra de progreso encontrada:")
                    print(f"   Progreso: {progress_info['progress']:.1f}%")
                    print(f"   Activa: {progress_info['is_active']}")
                else:
                    print("❌ No se encontró barra de progreso")
            elif command == '9':
                success = clicker.wait_for_progress_completion()
                if success:
                    print("✅ Progreso completado exitosamente")
                else:
                    print("⚠️ Progreso no completado o timeout")
            elif command.lower() == 'a':
                success = clicker.smart_completion_handler()
                if success:
                    print("✅ Finalización manejada exitosamente")
                else:
                    print("⚠️ No se pudo manejar la finalización")
            else:
                print("Comando no reconocido")
                
        except KeyboardInterrupt:
            print("\nSaliendo...")
            break
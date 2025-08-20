# -*- coding: utf-8 -*-
"""
Script de prueba para el sistema de detección IA
Ejecutar esto para probar si la IA puede detectar botones sin hacer clicks
"""

from ai_button_detector import AIButtonDetector
import time
import os

def test_ai_detection():
    print("🧪 === TEST DE DETECCIÓN IA ===")
    print("📋 Este script probará si la IA puede detectar botones en tu pantalla")
    print("⚠️ Asegúrate de tener abierta la ventana del instalador")
    print()
    
    input("📍 Posiciona la ventana del instalador y presiona Enter...")
    
    # Crear detector
    detector = AIButtonDetector(debug=True)
    
    print("\n🔍 Analizando pantalla actual...")
    
    # Detectar botones
    buttons = detector.find_best_buttons(min_confidence=0.1)  # Confianza más baja para testing
    
    if not buttons:
        print("❌ No se detectaron botones")
        print("\n💡 POSIBLES SOLUCIONES:")
        print("   • Asegúrate de que la ventana esté completamente visible")
        print("   • Prueba con diferentes instaladores")
        print("   • Verifica que tengas pytesseract instalado")
        print("   • Ejecuta como administrador")
        return False
    
    print(f"\n✅ ¡Detección exitosa! Se encontraron {len(buttons)} botones")
    
    # Mostrar detalles
    for i, button in enumerate(buttons):
        x, y, w, h = button['bbox']
        cx, cy = button['center']
        conf = button['confidence']
        method = button['method']
        
        print(f"\n🎯 Botón {i+1}:")
        print(f"   📍 Posición: ({cx}, {cy})")
        print(f"   📐 Tamaño: {w}x{h}")
        print(f"   🎲 Confianza: {conf:.2f}")
        print(f"   🔧 Método: {method}")
        
        if 'text' in button and button['text']:
            print(f"   📝 Texto detectado: '{button['text']}'")
        
        if 'detection_count' in button:
            print(f"   🔢 Detectado por {button['detection_count']} algoritmos")
    
    # Guardar imagen de debug
    debug_file = detector.save_detection_debug(buttons, "test_ai_detection_result.png")
    
    if debug_file:
        print(f"\n🖼️ Imagen con detecciones guardada en: {debug_file}")
        print("👀 ¡Abre esta imagen para ver los botones detectados!")
    
    print(f"\n📊 RESUMEN:")
    print(f"   ✅ Botones detectados: {len(buttons)}")
    print(f"   🎯 Mejor confianza: {max(b['confidence'] for b in buttons):.2f}")
    print(f"   🔧 Métodos usados: {len(set(b['method'] for b in buttons))}")
    
    # Contar por método
    method_count = {}
    for button in buttons:
        methods = button['method'].split('+')
        for method in methods:
            method_count[method] = method_count.get(method, 0) + 1
    
    print(f"\n📈 DETECCIONES POR MÉTODO:")
    for method, count in sorted(method_count.items(), key=lambda x: x[1], reverse=True):
        print(f"   • {method}: {count} detecciones")
    
    return True

if __name__ == "__main__":
    try:
        success = test_ai_detection()
        
        print(f"\n{'='*50}")
        if success:
            print("✅ TEST EXITOSO - La IA puede detectar botones")
            print("🚀 Ahora puedes usar los comandos 92, 93 y 99 en ui_clicker.py")
        else:
            print("❌ TEST FALLÓ - Revisar configuración")
        
        print("\n💡 PRÓXIMOS PASOS:")
        print("   1. Ejecuta ui_clicker.py")
        print("   2. Usa comando 93 para análisis IA")
        print("   3. Usa comando 92 para click IA")
        print("   4. Usa comando 99 para auto-instalación con IA")
        
    except Exception as e:
        print(f"\n❌ Error en test: {e}")
        print("🔧 Verifica que tengas instalado:")
        print("   pip install opencv-python pillow pytesseract numpy")
        
    input("\nPresiona Enter para salir...")
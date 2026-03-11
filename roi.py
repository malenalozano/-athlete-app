def get_float_input(prompt):
    """
    Solicita al usuario un número flotante. Si el usuario introduce un texto no válido,
    se le pedirá que lo intente nuevamente.
    """
    while True:
        try:
            return float(input(prompt))
        except ValueError:
            print("Entrada no válida. Por favor, introduce un número.")

def calculate_roi():
    """
    Calcula el Retorno de Inversión (ROI) basado en la ganancia neta y el costo de inversión.
    """
    print("Calculadora de Retorno de Inversión (ROI)")
    net_profit = get_float_input("Introduce la ganancia neta: ")
    investment_cost = get_float_input("Introduce el costo de la inversión: ")

    if investment_cost == 0:
        print("El costo de inversión no puede ser cero.")
        return

    roi = (net_profit / investment_cost) * 100
    print(f"El Retorno de Inversión (ROI) es: {roi:.2f}%")

if __name__ == "__main__":
    calculate_roi()

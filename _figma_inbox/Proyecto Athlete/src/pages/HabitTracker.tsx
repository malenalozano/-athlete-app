import React, { useState } from "react";
import { Card, Badge, Button, Table, Progress } from "../app/components/ui";

// Lista de hábitos sugeridos por defecto
const defaultHabits = [
  "Hidratación",
  "Estiramientos",
  "Foam Roller",
  "Meditación",
  "Suplementos",
  "10k Pasos",
  "Dormir 8h",
  "Comida Saludable",
  "No Azúcar",
  "No Alcohol",
  "Lectura",
  "Escribir Diario",
  "Entreno Fuerza",
  "Entreno Cardio",
  "Yoga",
  "Mindfulness",
  "Proteína",
  "Frutas y Verduras",
  "Desayuno Nutritivo",
  "Evitar Ultra Procesados",
  "Tiempo al Aire Libre",
  "Desconexión Digital",
  "Socializar",
  "Planificación Día",
  "Revisión Objetivos",
  "Tareas Prioritarias",
  "Cuidado Personal",
  "Postura Correcta",
  "Respiración",
  "Visualización",
  "Aprender Algo Nuevo"
];

const HabitTracker = () => {
  const [habits, setHabits] = useState(defaultHabits);
  // ...aquí irá la lógica y UI
  return (
    <div className="habit-tracker-page">
      <h1>Habit Tracker</h1>
      {/* Aquí irán los componentes principales: Score, Racha, Mejor Hábito, Mejor Día, Vista Semanal, Panel Hoy, Análisis */}
      <div>
        <h2>Hábitos disponibles</h2>
        <ul>
          {habits.map((habit) => (
            <li key={habit}>{habit}</li>
          ))}
        </ul>
        {/* Botón para añadir hábitos personalizados */}
        <Button>Añadir hábito</Button>
      </div>
    </div>
  );
};

export default HabitTracker;

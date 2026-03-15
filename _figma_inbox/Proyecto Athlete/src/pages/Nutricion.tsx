import React from "react";

// Datos de ejemplo
const dailyData = {
  calories: 2340,
  caloriesGoal: 2700,
  protein: 148,
  proteinGoal: 175,
  carbs: 285,
  carbsGoal: 340,
  fat: 68,
  fatGoal: 80,
  hydration: 2.1,
  hydrationGoal: 3,
};

const meals = [
  {
    name: "Desayuno",
    time: "07:30",
    kcal: 520,
    foods: [
      { name: "Arroz integral 150g", kcal: 210, carbs: 45, protein: 5, fat: 2 },
      { name: "Pechuga de pollo 180g", kcal: 290, carbs: 0, protein: 55, fat: 6 },
      { name: "Ensalada verde + aceite", kcal: 120, carbs: 8, protein: 2, fat: 10 },
      { name: "Fruta (naranja)", kcal: 60, carbs: 15, protein: 1, fat: 0 },
    ],
  },
  {
    name: "Almuerzo",
    time: "13:00",
    kcal: 780,
    foods: [],
  },
  { name: "Pre-Entreno", time: "16:30", kcal: 210, foods: [] },
  { name: "Cena", time: "20:00", kcal: 620, foods: [] },
];

const weeklyCalories = [
  { day: "Lun", value: 2600 },
  { day: "Mar", value: 2400 },
  { day: "Mié", value: 2800 },
  { day: "Jue", value: 2100 },
  { day: "Vie", value: 2700 },
  { day: "Sáb", value: 3100 },
  { day: "Dom", value: 2200 },
];

const NutritionPage: React.FC = () => {
  return (
    <div style={{ background: "#181A1B", color: "#fff", minHeight: "100vh", padding: "32px" }}>
      <h1 style={{ fontSize: "2rem", marginBottom: "24px" }}>Nutrición</h1>
      {/* Resumen macros */}
      <div style={{ display: "flex", gap: "16px", marginBottom: "32px" }}>
        <MacroCard label="Calorías" value={dailyData.calories} goal={dailyData.caloriesGoal} color="#FFB300" />
        <MacroCard label="Proteínas" value={dailyData.protein} goal={dailyData.proteinGoal} color="#B6FF00" />
        <MacroCard label="Carbohidratos" value={dailyData.carbs} goal={dailyData.carbsGoal} color="#00B6FF" />
        <MacroCard label="Grasas" value={dailyData.fat} goal={dailyData.fatGoal} color="#B300FF" />
        <MacroCard label="Hidratación" value={dailyData.hydration} goal={dailyData.hydrationGoal} color="#00FFF0" unit="L" />
      </div>
      {/* Comidas del día */}
      <div style={{ marginBottom: "32px" }}>
        <h2 style={{ fontSize: "1.2rem", marginBottom: "16px" }}>Comidas de hoy — 15 Mar 2026</h2>
        {meals.map((meal) => (
          <MealCard key={meal.name} meal={meal} />
        ))}
        <button style={{ marginTop: "16px", background: "#222", color: "#FFB300", border: "none", padding: "12px 24px", borderRadius: "8px", fontWeight: "bold" }}>
          + Añadir comida
        </button>
      </div>
      {/* Distribución macros y progreso */}
      <div style={{ display: "flex", gap: "32px" }}>
        <div style={{ flex: 1 }}>
          <h3 style={{ marginBottom: "8px" }}>Distribución Macros</h3>
          {/* Aquí iría el gráfico circular */}
          <div style={{ height: "200px", background: "#222", borderRadius: "16px" }}>
            {/* Placeholder gráfico */}
            <p style={{ textAlign: "center", paddingTop: "80px", color: "#B6FF00" }}>[Gráfico Macros]</p>
          </div>
        </div>
        <div style={{ flex: 1 }}>
          <h3 style={{ marginBottom: "8px" }}>Progreso del Día</h3>
          <ProgressBar label="Calorías" value={dailyData.calories} goal={dailyData.caloriesGoal} color="#FFB300" />
          <ProgressBar label="Proteínas" value={dailyData.protein} goal={dailyData.proteinGoal} color="#B6FF00" />
          <ProgressBar label="Carbohidratos" value={dailyData.carbs} goal={dailyData.carbsGoal} color="#00B6FF" />
          <ProgressBar label="Grasas" value={dailyData.fat} goal={dailyData.fatGoal} color="#B300FF" />
          <ProgressBar label="Hidratación" value={dailyData.hydration} goal={dailyData.hydrationGoal} color="#00FFF0" unit="L" />
        </div>
      </div>
      {/* Calorías semanales */}
      <div style={{ marginTop: "48px" }}>
        <h3 style={{ marginBottom: "8px" }}>Calorías esta semana</h3>
        <div style={{ height: "180px", background: "#222", borderRadius: "16px" }}>
          {/* Placeholder gráfico barras */}
          <p style={{ textAlign: "center", paddingTop: "70px", color: "#FFB300" }}>[Gráfico Calorías]</p>
        </div>
      </div>
    </div>
  );
};

// MacroCard
const MacroCard = ({ label, value, goal, color, unit = "g" }: any) => (
  <div style={{ background: "#222", borderRadius: "12px", padding: "24px", flex: 1 }}>
    <div style={{ color }}>{label}</div>
    <div style={{ fontSize: "1.5rem", fontWeight: "bold", margin: "8px 0" }}>{value} {unit}</div>
    <div style={{ fontSize: "0.9rem", color: "#888" }}>
      {unit === "L" ? `${value} / ${goal} L` : `${value} / ${goal} ${unit}`}
    </div>
    <div style={{ height: "6px", background: "#333", borderRadius: "4px", marginTop: "12px" }}>
      <div style={{ width: `${(value / goal) * 100}%`, height: "100%", background: color, borderRadius: "4px" }} />
    </div>
  </div>
);

// MealCard
const MealCard = ({ meal }: any) => (
  <div style={{ background: "#222", borderRadius: "12px", padding: "16px", marginBottom: "12px" }}>
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <div style={{ fontWeight: "bold" }}>{meal.name}</div>
      <div style={{ color: "#FFB300", fontWeight: "bold" }}>{meal.kcal} kcal</div>
    </div>
    <div style={{ fontSize: "0.9rem", color: "#888" }}>{meal.time}</div>
    {meal.foods && meal.foods.length > 0 && (
      <table style={{ width: "100%", marginTop: "8px", fontSize: "0.95rem" }}>
        <thead>
          <tr style={{ color: "#B6FF00" }}>
            <th style={{ textAlign: "left" }}>Alimento</th>
            <th>Kcal</th>
            <th>Carbs</th>
            <th>Prot</th>
            <th>Grasas</th>
          </tr>
        </thead>
        <tbody>
          {meal.foods.map((food: any, idx: number) => (
            <tr key={idx}>
              <td>{food.name}</td>
              <td>{food.kcal}</td>
              <td style={{ color: "#00B6FF" }}>{food.carbs}g</td>
              <td style={{ color: "#B6FF00" }}>{food.protein}g</td>
              <td style={{ color: "#B300FF" }}>{food.fat}g</td>
            </tr>
          ))}
        </tbody>
      </table>
    )}
  </div>
);

// ProgressBar
const ProgressBar = ({ label, value, goal, color, unit = "g" }: any) => (
  <div style={{ marginBottom: "12px" }}>
    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.95rem" }}>
      <span>{label}</span>
      <span style={{ color }}>{unit === "L" ? `${value} / ${goal} L` : `${value} / ${goal} ${unit}`}</span>
    </div>
    <div style={{ height: "6px", background: "#333", borderRadius: "4px", marginTop: "4px" }}>
      <div style={{ width: `${(value / goal) * 100}%`, height: "100%", background: color, borderRadius: "4px" }} />
    </div>
  </div>
);

export default NutritionPage;

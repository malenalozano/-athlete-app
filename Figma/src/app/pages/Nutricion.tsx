import { Header } from "../components/Header";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { useState } from "react";
import { Utensils, Target, TrendingUp, Droplets, Flame, Zap, Apple } from "lucide-react";
import {
  ResponsiveContainer, PieChart, Pie, Cell, Tooltip
} from "recharts";

const TABS = ["Tracking Diario", "Plan Semanal", "Recetas"] as const;
type Tab = typeof TABS[number];

// ── Data placeholders — TODO: fetch from nutrition API / Supabase ─────────────

// TODO: fetch today's macros from food log
const todayMacros = {
  kcal: { consumed: 0, target: 0 },
  proteinas: { consumed: 0, target: 0 },
  carbos: { consumed: 0, target: 0 },
  grasas: { consumed: 0, target: 0 },
  hidratacion: { consumed: 0, target: 0 },
};

// TODO: fetch macro distribution from today's food log
const macroDistribution: { name: string; value: number; color: string; pct: string }[] = [];

// TODO: fetch weekly nutrition plan (linked to training plan)
const weeklyPlan: {
  dia: string;
  tipo: string;
  desayuno: string;
  almuerzo: string;
  cena: string;
  kcal: number;
  carboFocus?: boolean;
  protFocus?: boolean;
}[] = [];

// ── Static recipe library (marathon-specific nutritional content) ─────────────
const recipes = [
  {
    name: "Bowl Pre-Maratón",
    category: "Pre-Carrera",
    emoji: "🏃",
    time: "10 min",
    kcal: 520,
    macros: { prot: 18, carbs: 88, fat: 8 },
    ingredients: ["200g arroz blanco cocido", "1 plátano maduro", "30g miel", "1 tbsp mantequilla de cacahuete", "Sal"],
    description: "Carga de glucógeno óptima. Consumir 2-3h antes de carrera larga o competición.",
    color: "border-[#C9FF00]/40 bg-[#C9FF00]/5",
    tags: ["Alta en carbos", "Pre-entreno"],
  },
  {
    name: "Batido Recuperación Muscular",
    category: "Post-Entreno",
    emoji: "💪",
    time: "5 min",
    kcal: 380,
    macros: { prot: 35, carbs: 42, fat: 6 },
    ingredients: ["30g proteína de suero", "1 plátano", "200ml leche desnatada", "50g avena", "1 tsp cúrcuma"],
    description: "Ventana anabólica: consumir dentro de los 30 min post-entreno para máxima recuperación.",
    color: "border-orange-500/40 bg-orange-500/5",
    tags: ["Alta en proteína", "Recuperación"],
  },
  {
    name: "Pasta Energética de Corredora",
    category: "Pre-Entreno (24h)",
    emoji: "🍝",
    time: "20 min",
    kcal: 680,
    macros: { prot: 32, carbs: 95, fat: 12 },
    ingredients: ["150g pasta integral", "150g pechuga de pollo", "Salsa de tomate natural", "30g parmesano", "Albahaca fresca", "AOVE"],
    description: "Cena perfecta la noche anterior a una carrera larga. Alta densidad de glucógeno.",
    color: "border-blue-500/40 bg-blue-500/5",
    tags: ["Carga de carbos", "Noche anterior"],
  },
  {
    name: "Bowl Anti-Inflamatorio",
    category: "Recuperación",
    emoji: "🥗",
    time: "15 min",
    kcal: 440,
    macros: { prot: 28, carbs: 38, fat: 18 },
    ingredients: ["200g salmón al horno", "150g quinoa", "Aguacate 1/2", "Edamame 80g", "Jengibre", "Semillas de chía"],
    description: "Rico en omega-3 y antioxidantes. Ideal para días de descanso o post-carrera larga.",
    color: "border-green-500/40 bg-green-500/5",
    tags: ["Antiinflamatorio", "Omega-3"],
  },
  {
    name: "Desayuno Maratón",
    category: "Día de Competición",
    emoji: "🏅",
    time: "10 min",
    kcal: 490,
    macros: { prot: 14, carbs: 82, fat: 10 },
    ingredients: ["100g avena instantánea", "1 plátano", "1 tbsp miel", "300ml leche", "Pasas 30g"],
    description: "Probado y seguro para el día de carrera. Sin fibra excesiva. 3h antes de la salida.",
    color: "border-yellow-500/40 bg-yellow-500/5",
    tags: ["Competición", "Seguro"],
  },
  {
    name: "Snack de Carrera (Geles caseros)",
    category: "Durante la Carrera",
    emoji: "⚡",
    time: "2 min",
    kcal: 120,
    macros: { prot: 0, carbs: 30, fat: 0 },
    ingredients: ["30g dátiles Medjool", "1/4 tsp sal marina", "1 tsp zumo de limón", "Opcional: 50mg cafeína"],
    description: "Alternativa natural a geles comerciales. Consumir cada 45 min durante el maratón.",
    color: "border-purple-500/40 bg-purple-500/5",
    tags: ["Durante carrera", "Natural"],
  },
];

function MacroBar({ label, consumed, target, unit, color }: { label: string; consumed: number; target: number; unit: string; color: string }) {
  const pct = target > 0 ? Math.min((consumed / target) * 100, 100) : 0;
  return (
    <div>
      <div className="flex justify-between mb-1">
        <span className="text-xs text-[#8B949E]">{label}</span>
        <span className="text-xs text-white font-semibold">{consumed}{unit} / {target}{unit}</span>
      </div>
      <div className="w-full bg-[#30363D] rounded-full h-2">
        <div className="h-2 rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
    </div>
  );
}

export function Nutricion() {
  const [activeTab, setActiveTab] = useState<Tab>("Tracking Diario");

  return (
    <div className="min-h-screen bg-[#0E1117]">
      <Header />

      <main className="container mx-auto px-6 py-8 space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-semibold text-white flex items-center gap-2">
            <Utensils className="h-6 w-6 text-[#C9FF00]" />
            Nutrición
          </h2>
          <div className="flex items-center gap-2 px-3 py-1.5 bg-[#C9FF00]/10 border border-[#C9FF00]/30 rounded-lg">
            <Target className="h-4 w-4 text-[#C9FF00]" />
            <span className="text-[#C9FF00] text-xs font-semibold">Objetivo: Maratón Sub 4h</span>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 border-b border-[#30363D] pb-0">
          {TABS.map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-5 py-2.5 text-sm font-medium transition-all border-b-2 -mb-px ${
                activeTab === tab
                  ? "border-[#C9FF00] text-[#C9FF00]"
                  : "border-transparent text-[#8B949E] hover:text-white"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* ==================== TRACKING DIARIO ==================== */}
        {activeTab === "Tracking Diario" && (
          <div className="space-y-6">
            {/* KPIs del día */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              {[
                { label: "Kcal", consumed: todayMacros.kcal.consumed, target: todayMacros.kcal.target, unit: "kcal", icon: Flame, color: "#f97316" },
                { label: "Proteínas", consumed: todayMacros.proteinas.consumed, target: todayMacros.proteinas.target, unit: "g", icon: Zap, color: "#C9FF00" },
                { label: "Carbos", consumed: todayMacros.carbos.consumed, target: todayMacros.carbos.target, unit: "g", icon: Apple, color: "#3b82f6" },
                { label: "Grasas", consumed: todayMacros.grasas.consumed, target: todayMacros.grasas.target, unit: "g", icon: TrendingUp, color: "#8b5cf6" },
                { label: "Hidratación", consumed: todayMacros.hidratacion.consumed, target: todayMacros.hidratacion.target, unit: "L", icon: Droplets, color: "#06b6d4" },
              ].map((kpi, i) => {
                const pct = kpi.target > 0 ? Math.min(Math.round((kpi.consumed / kpi.target) * 100), 100) : 0;
                const Icon = kpi.icon;
                return (
                  <Card key={i} className="bg-[#161B22] border border-[#30363D] rounded-xl">
                    <CardContent className="pt-4 pb-4">
                      <div className="flex items-center justify-between mb-2">
                        <Icon className="h-4 w-4" style={{ color: kpi.color }} />
                        <span className="text-[10px] text-[#8B949E] uppercase font-bold">{pct}%</span>
                      </div>
                      <p className="text-lg font-bold text-white">{kpi.consumed}<span className="text-xs text-[#8B949E] ml-1">{kpi.unit}</span></p>
                      <p className="text-[10px] text-[#8B949E]">{kpi.label} / {kpi.target}{kpi.unit}</p>
                      <div className="mt-2 w-full bg-[#30363D] rounded-full h-1.5">
                        <div className="h-1.5 rounded-full" style={{ width: `${pct}%`, backgroundColor: kpi.color }} />
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>

            {/* Distribución macros y progreso */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Pie de macros */}
              <Card className="bg-[#161B22] border border-[#30363D] rounded-xl">
                <CardHeader>
                  <CardTitle className="text-white text-sm">Distribución Macros</CardTitle>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={160}>
                    <PieChart>
                      <Pie
                        data={macroDistribution}
                        cx="50%" cy="50%"
                        innerRadius={45} outerRadius={70}
                        paddingAngle={2}
                        dataKey="value"
                      >
                        {macroDistribution.map((entry, i) => (
                          <Cell key={i} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{ backgroundColor: '#161B22', border: '1px solid #C9FF00' }}
                        formatter={(v: any, n: any, props: any) => [`${v}g (${props.payload.pct})`, props.payload.name]}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="space-y-2 mt-2">
                    {macroDistribution.map((m, i) => (
                      <div key={i} className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: m.color }}></div>
                          <span className="text-xs text-[#8B949E]">{m.name}</span>
                        </div>
                        <span className="text-xs font-bold text-white">{m.value}g <span className="text-[#8B949E] font-normal">{m.pct}</span></span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Barras de progreso */}
              <Card className="bg-[#161B22] border border-[#30363D] rounded-xl">
                <CardHeader>
                  <CardTitle className="text-white text-sm">Progreso del Día</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <MacroBar label="Calorías" consumed={todayMacros.kcal.consumed} target={todayMacros.kcal.target} unit=" kcal" color="#f97316" />
                  <MacroBar label="Proteínas" consumed={todayMacros.proteinas.consumed} target={todayMacros.proteinas.target} unit="g" color="#C9FF00" />
                  <MacroBar label="Carbohidratos" consumed={todayMacros.carbos.consumed} target={todayMacros.carbos.target} unit="g" color="#3b82f6" />
                  <MacroBar label="Grasas" consumed={todayMacros.grasas.consumed} target={todayMacros.grasas.target} unit="g" color="#8b5cf6" />
                  <MacroBar label="Hidratación" consumed={todayMacros.hidratacion.consumed} target={todayMacros.hidratacion.target} unit=" L" color="#06b6d4" />
                </CardContent>
              </Card>
            </div>
          </div>
        )}

        {/* ==================== PLAN SEMANAL ==================== */}
        {activeTab === "Plan Semanal" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <p className="text-[#8B949E] text-sm">Plan nutricional adaptado al entrenamiento de maratón — Semana 9-15 Mar 2026</p>
              <div className="flex gap-4 text-xs">
                <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded bg-[#C9FF00]/30 border border-[#C9FF00]/60"></div><span className="text-[#8B949E]">Carga de carbos</span></div>
                <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded bg-orange-500/30 border border-orange-500/60"></div><span className="text-[#8B949E]">Carga de proteínas</span></div>
              </div>
            </div>

            <div className="space-y-3">
              {weeklyPlan.map((day, i) => (
                <Card key={i} className={`border rounded-xl ${
                  day.carboFocus ? "bg-[#C9FF00]/5 border-[#C9FF00]/20" :
                  day.protFocus ? "bg-orange-500/5 border-orange-500/20" :
                  "bg-[#161B22] border-[#30363D]"
                }`}>
                  <CardContent className="pt-4 pb-4">
                    <div className="grid grid-cols-1 md:grid-cols-6 gap-4 items-start">
                      <div>
                        <p className="text-white font-bold text-sm">{day.dia}</p>
                        <p className="text-[#8B949E] text-xs mt-0.5">{day.tipo}</p>
                        <p className={`text-sm font-bold mt-2 ${day.carboFocus ? "text-[#C9FF00]" : day.protFocus ? "text-orange-400" : "text-[#8B949E]"}`}>
                          {day.kcal} kcal
                        </p>
                        {day.carboFocus && <span className="text-[9px] text-[#C9FF00] border border-[#C9FF00]/40 rounded px-1">CARBO↑</span>}
                        {day.protFocus && <span className="text-[9px] text-orange-400 border border-orange-400/40 rounded px-1">PROT↑</span>}
                      </div>
                      <div className="md:col-span-5 grid grid-cols-1 md:grid-cols-3 gap-3">
                        {[
                          { label: "🌅 Desayuno", content: day.desayuno },
                          { label: "☀️ Almuerzo", content: day.almuerzo },
                          { label: "🌙 Cena", content: day.cena },
                        ].map(meal => (
                          <div key={meal.label} className="bg-[#0E1117]/60 rounded-lg p-3">
                            <p className="text-xs font-semibold text-[#8B949E] mb-1">{meal.label}</p>
                            <p className="text-xs text-white">{meal.content}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            {/* Notas nutricionales */}
            <Card className="bg-[#161B22] border border-[#C9FF00]/20 rounded-xl">
              <CardHeader>
                <CardTitle className="text-white text-sm">💡 Principios Nutricionales — Maratón</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {[
                    { title: "Carbohidratos", icon: "🍚", desc: "5-7g/kg/día en días normales. 8-10g/kg/día en días de carrera larga. Priorizar fuentes de bajo IG." },
                    { title: "Proteínas", icon: "🥩", desc: "1.6-1.8g/kg/día para corredores de maratón. Distribuir en 4-5 tomas. Post-entreno: 25-40g." },
                    { title: "Grasas", icon: "🥑", desc: "25-30% de las calorías. Omega-3 anti-inflamatorios clave. Evitar grasas saturadas el día de carrera." },
                  ].map((p, i) => (
                    <div key={i} className="bg-[#0E1117] rounded-lg p-4">
                      <p className="text-base mb-2">{p.icon} <span className="text-white font-semibold text-sm">{p.title}</span></p>
                      <p className="text-xs text-[#8B949E]">{p.desc}</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* ==================== RECETAS ==================== */}
        {activeTab === "Recetas" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <p className="text-[#8B949E] text-sm">Recetas específicas para entrenamiento de maratón</p>
              <div className="flex gap-2">
                {["Pre-Carrera", "Post-Entreno", "Recuperación", "Competición"].map(tag => (
                  <span key={tag} className="text-[10px] px-2 py-1 border border-[#30363D] rounded-full text-[#8B949E] hover:border-[#C9FF00]/40 hover:text-white cursor-pointer transition-all">
                    {tag}
                  </span>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
              {recipes.map((recipe, i) => (
                <Card key={i} className={`border rounded-xl ${recipe.color}`}>
                  <CardContent className="pt-5 pb-5">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <span className="text-2xl">{recipe.emoji}</span>
                        <p className="text-white font-bold text-sm mt-1">{recipe.name}</p>
                        <p className="text-[10px] text-[#8B949E]">{recipe.category}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-[#C9FF00] font-bold">{recipe.kcal}</p>
                        <p className="text-[10px] text-[#8B949E]">kcal</p>
                        <p className="text-[10px] text-[#8B949E] mt-1">⏱ {recipe.time}</p>
                      </div>
                    </div>

                    {/* Macros mini */}
                    <div className="flex gap-3 mb-3 text-xs">
                      <span className="text-[#C9FF00]">P: {recipe.macros.prot}g</span>
                      <span className="text-blue-400">C: {recipe.macros.carbs}g</span>
                      <span className="text-purple-400">G: {recipe.macros.fat}g</span>
                    </div>

                    <p className="text-xs text-[#8B949E] mb-3">{recipe.description}</p>

                    <div className="space-y-1 mb-3">
                      {recipe.ingredients.slice(0, 3).map((ing, j) => (
                        <div key={j} className="flex items-center gap-1.5">
                          <div className="w-1 h-1 rounded-full bg-[#C9FF00]/60"></div>
                          <span className="text-xs text-[#8B949E]">{ing}</span>
                        </div>
                      ))}
                      {recipe.ingredients.length > 3 && (
                        <p className="text-xs text-[#8B949E]/60">+{recipe.ingredients.length - 3} ingredientes más</p>
                      )}
                    </div>

                    <div className="flex flex-wrap gap-1">
                      {recipe.tags.map((tag, j) => (
                        <span key={j} className="text-[9px] px-2 py-0.5 bg-[#0E1117] rounded-full border border-[#30363D] text-[#8B949E]">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            {/* Suplementación */}
            <Card className="bg-[#161B22] border border-[#30363D] rounded-xl">
              <CardHeader>
                <CardTitle className="text-white text-sm flex items-center gap-2">
                  <Zap className="h-4 w-4 text-[#C9FF00]" />
                  Suplementación Recomendada para Maratón
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  {[
                    { name: "Proteína Whey", when: "Post-entreno", dose: "25-35g", desc: "Recuperación muscular óptima en ventana anabólica", emoji: "💪" },
                    { name: "Creatina", when: "Diario", dose: "5g", desc: "Mejora rendimiento en sprints y recuperación. Carga: 20g/día 5 días", emoji: "⚡" },
                    { name: "Omega-3", when: "Con comidas", dose: "2-3g EPA+DHA", desc: "Reduce inflamación post-carrera larga. Clave en período de volumen", emoji: "🐟" },
                    { name: "Hierro + Vitamina C", when: "Mañana", dose: "18mg + 500mg", desc: "Crucial en corredoras. Optimiza transporte de oxígeno. Analítica cada 3 meses", emoji: "🩸" },
                    { name: "Vitamina D3 + K2", when: "Con comida grasa", dose: "2000-4000 UI", desc: "Salud ósea y muscular. Esencial en meses de invierno. Medir niveles", emoji: "☀️" },
                    { name: "Magnesio Glicinato", when: "Noche", dose: "300-400mg", desc: "Reduce calambres, mejora sueño y recuperación. Mejor tolerado que óxido", emoji: "🌙" },
                    { name: "Beta-Alanina", when: "Pre-entreno", dose: "3.2g", desc: "Retrasa fatiga muscular en umbrales. Hormigueo cutáneo normal", emoji: "🔥" },
                    { name: "Electrolitos", when: "Durante carrera", dose: "500mg Na/h", desc: "Sodio, Potasio, Magnesio. Clave en carreras >1h. Geles salados", emoji: "💧" },
                  ].map((supp, i) => (
                    <div key={i} className="bg-[#0E1117] rounded-xl p-4 border border-[#30363D]">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-xl">{supp.emoji}</span>
                        <div>
                          <p className="text-white text-xs font-bold">{supp.name}</p>
                          <p className="text-[#C9FF00] text-[10px]">{supp.dose} · {supp.when}</p>
                        </div>
                      </div>
                      <p className="text-[10px] text-[#8B949E]">{supp.desc}</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </main>
    </div>
  );
}
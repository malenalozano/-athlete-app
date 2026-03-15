import { createBrowserRouter } from "react-router";
import { Home } from "./pages/Home";
import { Profile } from "./pages/Profile";
import { PersonalTrainer } from "./pages/PersonalTrainer";
import { CicloMenstrual } from "./pages/CicloMenstrual";
import { BibliotecaCientifica } from "./pages/BibliotecaCientifica";
import { DiarioFuerza } from "./pages/DiarioFuerza";
import { Calendario } from "./pages/Calendario";

import HabitTracker from "./pages/HabitTracker";
import NutritionPage from "./pages/Nutricion";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: Home,
  },
  {
    path: "/perfil",
    Component: Profile,
  },
  {
    path: "/ciclo-menstrual",
    Component: CicloMenstrual,
  },
  {
    path: "/biblioteca",
    Component: BibliotecaCientifica,
  },
  {
    path: "/diario-fuerza",
    Component: DiarioFuerza,
  },
  {
    path: "/entrenador",
    Component: PersonalTrainer,
  },
  {
    path: "/calendario",
    Component: Calendario,
  },
  {
    path: "/habit-tracker",
    Component: HabitTracker,
  },
  {
    path: "/nutricion",
    Component: NutritionPage,
  },
]);
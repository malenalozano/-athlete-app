import { createBrowserRouter } from "react-router";
import { Home } from "./pages/Home";
import { Profile } from "./pages/Profile";
import { PersonalTrainer } from "./pages/PersonalTrainer";
import { CicloMenstrual } from "./pages/CicloMenstrual";
import { BibliotecaCientifica } from "./pages/BibliotecaCientifica";
import { DiarioFuerza } from "./pages/DiarioFuerza";
import { Calendario } from "./pages/Calendario";
import { Habitos } from "./pages/Habitos";
import { Nutricion } from "./pages/Nutricion";
import { PlanSemanal } from "./pages/PlanSemanal";
import { Diario } from "./pages/Diario";
import { Garmin } from "./pages/Garmin";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: Home,
  },
  {
    path: "/plan-semanal",
    Component: PlanSemanal,
  },
  {
    path: "/diario",
    Component: Diario,
  },
  {
    path: "/calendario",
    Component: Calendario,
  },
  {
    path: "/garmin",
    Component: Garmin,
  },
  // Legacy / still accessible routes
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
    path: "/habitos",
    Component: Habitos,
  },
  {
    path: "/nutricion",
    Component: Nutricion,
  },
]);

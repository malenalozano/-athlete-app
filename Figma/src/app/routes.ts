import { createBrowserRouter } from "react-router";
import { LandingPage } from "./pages/LandingPage";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: LandingPage,
  },
  {
    path: "/dashboard",
    lazy: async () => {
      const { Home } = await import("./pages/Home");
      return { Component: Home };
    },
  },
  {
    path: "/plan-semanal",
    lazy: async () => {
      const { PlanSemanal } = await import("./pages/PlanSemanal");
      return { Component: PlanSemanal };
    },
  },
  {
    path: "/diario",
    lazy: async () => {
      const { Diario } = await import("./pages/Diario");
      return { Component: Diario };
    },
  },
  {
    path: "/calendario",
    lazy: async () => {
      const { Calendario } = await import("./pages/Calendario");
      return { Component: Calendario };
    },
  },
  {
    path: "/perfil",
    lazy: async () => {
      const { Profile } = await import("./pages/Profile");
      return { Component: Profile };
    },
  },
  {
    path: "/ejercicios",
    lazy: async () => {
      const { Ejercicios } = await import("./pages/Ejercicios");
      return { Component: Ejercicios };
    },
  },
  {
    path: "/entrenador",
    lazy: async () => {
      const { PersonalTrainer } = await import("./pages/PersonalTrainer");
      return { Component: PersonalTrainer };
    },
  },
  {
    path: "/ciclo-menstrual",
    lazy: async () => {
      const { CicloMenstrual } = await import("./pages/CicloMenstrual");
      return { Component: CicloMenstrual };
    },
  },
]);

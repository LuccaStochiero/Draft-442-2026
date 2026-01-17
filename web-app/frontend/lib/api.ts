import { DraftState, Player } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
const ROOT_URL = process.env.NEXT_PUBLIC_API_URL ? process.env.NEXT_PUBLIC_API_URL.replace('/api', '') : "http://localhost:8000/";

export const api = {
    getSetupState: async () => {
        // Check if root returns setup: true
        const res = await fetch(`${ROOT_URL}`);
        return res.json();
    },

    setupDraft: async (league_name: string, teams: { name: string, logo: string }[], n_rounds: number) => {
        const res = await fetch(`${API_URL}/setup`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ league_name, teams, n_rounds, random_order: false }), // Enforce strict order
        });
        return res.json();
    },

    getState: async (): Promise<DraftState> => {
        const res = await fetch(`${API_URL}/state`);
        return res.json();
    },

    getPlayers: async (): Promise<Player[]> => {
        const res = await fetch(`${API_URL}/players`);
        return res.json();
    },

    makePick: async (team_idx: number, player_name: string) => {
        const res = await fetch(`${API_URL}/pick`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ team_idx, player_name }),
        });
        if (!res.ok) throw new Error("Pick failed");
        return res.json();
    },

    resetDraft: async () => {
        const res = await fetch(`${API_URL}/reset`, { method: "POST" });
        return res.json();
    },

    undoPick: async () => {
        const res = await fetch(`${API_URL}/undo`, { method: "POST" });
        if (!res.ok) throw new Error("Undo failed");
        return res.json();
    },

    getExportUrl: () => `${API_URL}/export`
};

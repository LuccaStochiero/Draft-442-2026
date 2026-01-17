import { DraftState } from "@/types";

interface DraftBoardProps {
    state: DraftState;
}

export function DraftBoard({ state }: DraftBoardProps) {
    const { n_rounds } = { n_rounds: 10, ...state }; // fallback
    const rounds = Array.from({ length: Math.ceil(state.total_picks / state.teams.length) }, (_, i) => i + 1);

    const historyMap = new Map();
    state.history.forEach(h => {
        historyMap.set(`${h.team_idx}-${h.round}`, h.player);
    });

    const posConfig = (pos: string) => {
        switch (pos) {
            case "Forward": return { color: "bg-[#D90429]", label: "ATA" };
            case "Midfielder": return { color: "bg-[#F2994A]", label: "MEI" };
            case "Defender": return { color: "bg-[#8E44AD]", label: "DEF" }; // Purple
            case "Goalkeeper": return { color: "bg-[#EC4899]", label: "GOL" }; // Pink
            default: return { color: "bg-gray-700", label: pos.substring(0, 3) };
        }
    }

    return (
        <div className="overflow-auto h-full p-6 bg-black/40 border border-white/5 rounded-xl custom-scrollbar relative">
            <h2 className="text-2xl font-oswald font-bold uppercase mb-6 sticky left-0 text-white z-10">Draft Board</h2>

            <div className="relative">
                <table className="w-full border-collapse">
                    <thead>
                        <tr>
                            {/* Top-Left Corner (Highest Z-Index - 50) */}
                            <th className="p-3 text-left text-sm font-bold uppercase text-gray-500 sticky left-0 top-0 bg-[#111] z-50 w-24 border-b border-white/10 shadow-[2px_2px_5px_rgba(0,0,0,0.5)]">
                                Round
                            </th>

                            {/* Team Headers (Z-Index - 40) */}
                            {state.teams.map(t => (
                                <th key={t.id} className="p-3 text-left min-w-[180px] border-b border-white/10 bg-[#111] sticky top-0 z-40 shadow-[0_2px_5px_rgba(0,0,0,0.5)]">
                                    <div className="text-base font-bold truncate text-white">{t.name}</div>
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {rounds.map(r => (
                            <tr key={r} className="border-b border-white/5 hover:bg-white/5 transition-colors group">
                                {/* Round Number Column (Z-Index - 30) */}
                                <td className="p-3 sticky left-0 bg-[#09090b] text-sm font-mono text-gray-500 border-r border-white/10 font-bold z-30 shadow-[2px_0_5px_rgba(0,0,0,0.5)] group-hover:bg-[#111] transition-colors">
                                    R{r}
                                </td>

                                {state.teams.map(t => {
                                    const player = historyMap.get(`${t.id}-${r}`);
                                    const config = player ? posConfig(player['Posição']) : null;

                                    return (
                                        <td key={t.id} className="p-3 bg-transparent z-10 relative">
                                            {player && config ? (
                                                <div className="flex items-center gap-3">
                                                    <div className={`w-1.5 h-10 rounded-full ${config.color}`}></div>
                                                    <div className="overflow-hidden">
                                                        <div className="text-sm font-bold truncate text-white">{player.Nome}</div>
                                                        <div className="text-[10px] text-gray-400 font-mono truncate font-bold">{config.label}</div>
                                                    </div>
                                                </div>
                                            ) : (
                                                <div className="h-10 rounded bg-white/5 border border-white/5 border-dashed"></div>
                                            )}
                                        </td>
                                    );
                                })}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

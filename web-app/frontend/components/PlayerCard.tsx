import { Player } from "@/types";
import { motion } from "framer-motion";
import { Shield, User } from "lucide-react";

interface PlayerCardProps {
    player: Player;
    onSelect?: () => void;
    compact?: boolean;
}

export function PlayerCard({ player, onSelect, compact = false }: PlayerCardProps) {
    const posConfig = (pos: string) => {
        switch (pos) {
            case "Forward": return { color: "bg-[#D90429] text-white", label: "ATA" };
            case "Midfielder": return { color: "bg-[#F2994A] text-black", label: "MEI" };
            case "Defender": return { color: "bg-[#8E44AD] text-white", label: "DEF" };
            case "Goalkeeper": return { color: "bg-[#EC4899] text-white", label: "GOL" }; // Pink
            default: return { color: "bg-gray-700 text-white", label: pos.substring(0, 3).toUpperCase() };
        }
    }

    const { color, label } = posConfig(player['Posição']);

    if (compact) {
        return (
            <div
                onClick={onSelect}
                className="group flex items-center justify-between p-3 bg-[#18181b] rounded border border-white/5 hover:border-neon-green/50 hover:bg-white/5 cursor-pointer transition-all"
            >
                <div className="flex items-center gap-4 overflow-hidden">
                    {/* Position Dot */}
                    <div className={`w-10 h-10 rounded shrink-0 flex items-center justify-center text-xs font-bold shadow-sm ${color}`}>
                        {label}
                    </div>

                    <div className="min-w-0">
                        <div className="text-base font-bold text-gray-200 truncate group-hover:text-white">{player.Nome}</div>
                        <div className="text-xs text-gray-400 uppercase flex items-center gap-1 truncate font-bold">
                            <span>{player.Team}</span>
                            {player['Número'] && <span>• #{player['Número']}</span>}
                        </div>
                    </div>
                </div>

                <div className="pl-2 text-right">
                    <div className="font-mono text-neon-green text-base font-bold">
                        €{player['Valor de Mercado']}M
                    </div>
                </div>
            </div>
        )
    }

    // Large Card (For Roster/Main View)
    return (
        <motion.div
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={onSelect}
            className={`group relative cursor-pointer bg-gradient-to-br from-[#1c1c1c] to-[#141414] border border-white/10 hover:border-white/30 rounded-xl overflow-hidden shadow-xl`}
        >
            {/* Top Bar Color */}
            <div className={`absolute top-0 left-0 w-full h-1.5 ${color.split(' ')[0]}`}></div>

            <div className="p-5 flex flex-col gap-3">
                <div className="flex justify-between items-start">
                    <div className={`px-3 py-1 rounded text-sm font-black uppercase tracking-wider ${color}`}>
                        {label}
                    </div>
                    <div className="text-sm text-gray-500 font-mono font-bold">#{player['Número'] || '--'}</div>
                </div>

                <div className="py-2">
                    <h3 className="text-2xl font-bold font-oswald truncate group-hover:text-[#39ff14] transition-colors text-white">
                        {player.Nome}
                    </h3>
                    <div className="flex items-center gap-1.5 text-base text-gray-400 font-medium">
                        <Shield size={14} />
                        <span>{player.Team}</span>
                    </div>
                </div>

                <div className="mt-2 pt-3 border-t border-white/5 flex justify-between items-end">
                    <div className="flex flex-col">
                        <span className="text-xs text-gray-500 uppercase font-bold">Valor</span>
                        <span className="text-xl font-bold text-white">€{player['Valor de Mercado']}M</span>
                    </div>

                    <button className="bg-white/10 p-2.5 rounded-full group-hover:bg-[#39ff14] group-hover:text-black transition-colors text-white">
                        <User size={20} />
                    </button>
                </div>
            </div>
        </motion.div>
    );
}

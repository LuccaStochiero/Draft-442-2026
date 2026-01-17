import { motion } from "framer-motion";

interface DraftHeaderProps {
    leagueName: string;
    round: number;
    pick: number;
    activeTeamName: string;
    activeTeamLogo?: string;
}

export function DraftHeader({ leagueName, round, pick, activeTeamName, activeTeamLogo }: DraftHeaderProps) {
    return (
        <div className="w-full bg-black/50 border-b border-white/10 p-4 sticky top-0 z-50 backdrop-blur-md">
            <div className="max-w-7xl mx-auto flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold uppercase tracking-wider text-white">
                        {leagueName}
                    </h1>
                </div>

                <div className="flex items-center gap-8">
                    <div className="flex flex-col items-center">
                        <span className="text-[10px] text-gray-500 uppercase tracking-widest">Rodada</span>
                        <span className="text-2xl font-oswald font-bold text-neon-green">{round}</span>
                    </div>
                    <div className="flex flex-col items-center">
                        <span className="text-[10px] text-gray-500 uppercase tracking-widest">Pick</span>
                        <span className="text-2xl font-oswald font-bold text-white">#{pick}</span>
                    </div>

                    <div className="h-8 w-px bg-white/10"></div>

                    <div className="flex items-center gap-4">
                        <div className="text-right hidden md:block">
                            <div className="text-[10px] text-gray-500 uppercase tracking-widest mb-1">Sua Vez</div>
                            <motion.div
                                initial={{ opacity: 0, x: -10 }}
                                animate={{ opacity: 1, x: 0 }}
                                key={activeTeamName}
                                className="text-xl font-bold text-neon-purple leading-none"
                            >
                                {activeTeamName}
                            </motion.div>
                        </div>

                        {activeTeamLogo && (
                            <motion.div
                                initial={{ scale: 0.8, opacity: 0 }}
                                animate={{ scale: 1, opacity: 1 }}
                                key={`logo-${activeTeamName}`}
                                className="w-12 h-12 rounded-full border-2 border-neon-purple bg-black p-1 shadow-[0_0_15px_rgba(191,0,255,0.4)]"
                            >
                                <img src={activeTeamLogo} className="w-full h-full object-cover rounded-full" />
                            </motion.div>
                        )}
                    </div>
                </div>

                <div className="flex items-center">
                    <div className="px-3 py-1 rounded bg-red-600/10 text-red-500 text-[10px] font-bold uppercase border border-red-600/30 animate-pulse flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-red-500"></span>
                        Ao Vivo
                    </div>
                </div>
            </div>
        </div>
    );
}

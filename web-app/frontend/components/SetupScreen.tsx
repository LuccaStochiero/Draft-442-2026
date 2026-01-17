import { useState, ChangeEvent } from "react";
import { api } from "@/lib/api";
import { Upload, X } from "lucide-react";

interface SetupScreenProps {
    onSetupComplete: () => void;
}

interface TeamSetup {
    name: string;
    logo: string; // base64
}

export function SetupScreen({ onSetupComplete }: SetupScreenProps) {
    const [leagueName, setLeagueName] = useState("Brasileirão Fantasy");
    const [nTeams, setNTeams] = useState(4);
    const [nRounds, setNRounds] = useState(10);
    const [teams, setTeams] = useState<TeamSetup[]>(
        Array(4).fill("").map((_, i) => ({ name: `Time ${i + 1}`, logo: "" }))
    );
    const [loading, setLoading] = useState(false);

    const handleCreate = async () => {
        if (teams.some(t => !t.name.trim())) {
            alert("Preencha o nome de todos os times!");
            return;
        }
        setLoading(true);
        try {
            await api.setupDraft(leagueName, teams, nRounds);
            onSetupComplete();
        } catch (e) {
            alert("Erro ao criar liga");
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const updateTeamName = (idx: number, name: string) => {
        const newTeams = [...teams];
        newTeams[idx].name = name;
        setTeams(newTeams);
    };

    const handleLogoUpload = (idx: number, e: ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            const reader = new FileReader();
            reader.onloadend = () => {
                const newTeams = [...teams];
                newTeams[idx].logo = reader.result as string;
                setTeams(newTeams);
            };
            reader.readAsDataURL(file);
        }
    };

    const updateNTeams = (n: number) => {
        setNTeams(n);
        const newTeams = [...teams];
        if (n > newTeams.length) {
            for (let i = newTeams.length; i < n; i++) {
                newTeams.push({ name: `Time ${i + 1}`, logo: "" });
            }
        } else {
            newTeams.length = n;
        }
        setTeams(newTeams);
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-[url('/bg-stadium.jpg')] bg-cover bg-center relative">
            <div className="absolute inset-0 bg-black/80 backdrop-blur-md"></div>

            <div className="relative z-10 w-full max-w-4xl bg-[#18181b] border border-white/10 p-8 rounded-2xl shadow-2xl max-h-[90vh] overflow-y-auto custom-scrollbar">
                <div className="mb-10 text-center border-b border-white/10 pb-8">
                    <h2 className="text-xl md:text-3xl font-black text-[#FFD700] uppercase leading-tight drop-shadow-[0_0_15px_rgba(255,215,0,0.5)] animate-pulse">
                        PARABÉNS AO CAMPEÃO DA 1º EDIÇÃO DO 442 KBR BRASILEIRÃO BETANO FANTASY GAME 2025 (1ª EDIÇÃO)
                    </h2>
                </div>

                <h1 className="text-2xl font-oswald font-bold text-center mb-8 text-gray-400 uppercase tracking-widest">
                    CONFIGURAÇÃO DA NOVA LIGA
                </h1>

                <div className="space-y-8">
                    {/* General Settings */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="md:col-span-1">
                            <label className="text-xs uppercase font-bold text-gray-500 mb-1 block">Nome da Liga</label>
                            <input
                                type="text"
                                className="w-full bg-black/40 border border-white/10 rounded-lg p-3 font-bold focus:border-neon-purple outline-none transition-colors"
                                value={leagueName}
                                onChange={e => setLeagueName(e.target.value)}
                            />
                        </div>
                        <div>
                            <label className="text-xs uppercase font-bold text-gray-500 mb-1 block">Qtd. Times</label>
                            <input
                                type="number"
                                className="w-full bg-black/40 border border-white/10 rounded-lg p-3 focus:border-neon-green outline-none"
                                value={nTeams}
                                onChange={(e) => updateNTeams(parseInt(e.target.value))}
                                min={2} max={20}
                            />
                        </div>
                        <div>
                            <label className="text-xs uppercase font-bold text-gray-500 mb-1 block">Rodadas</label>
                            <input
                                type="number"
                                className="w-full bg-black/40 border border-white/10 rounded-lg p-3 focus:border-neon-green outline-none"
                                value={nRounds}
                                onChange={(e) => setNRounds(parseInt(e.target.value))}
                                min={1} max={30}
                            />
                        </div>
                    </div>

                    <div className="h-px bg-white/10"></div>

                    {/* Teams Config */}
                    <div>
                        <label className="text-xs uppercase font-bold text-gray-500 mb-4 block">Participantes (Ordem do Draft)</label>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {teams.map((team, i) => (
                                <div key={i} className="bg-black/30 border border-white/5 rounded-xl p-4 flex items-center gap-4 hover:border-white/20 transition-colors group">
                                    <div className="flex-shrink-0 relative">
                                        <div className="w-16 h-16 rounded-full bg-black/50 border border-white/10 flex items-center justify-center overflow-hidden">
                                            {team.logo ? (
                                                <img src={team.logo} alt="logo" className="w-full h-full object-cover" />
                                            ) : (
                                                <Upload size={20} className="text-gray-600 group-hover:text-neon-green transition-colors" />
                                            )}
                                        </div>
                                        <input
                                            type="file"
                                            accept="image/*"
                                            className="absolute inset-0 opacity-0 cursor-pointer"
                                            onChange={(e) => handleLogoUpload(i, e)}
                                        />
                                    </div>
                                    <div className="flex-1">
                                        <div className="text-[10px] uppercase text-gray-500 font-bold mb-1">Time #{i + 1}</div>
                                        <input
                                            type="text"
                                            className="w-full bg-transparent border-b border-white/10 py-1 text-lg font-bold focus:border-neon-green outline-none"
                                            value={team.name}
                                            onChange={(e) => updateTeamName(i, e.target.value)}
                                            placeholder="Nome do Time"
                                        />
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    <button
                        onClick={handleCreate}
                        disabled={loading}
                        className="w-full bg-[#39ff14] hover:bg-[#32e010] text-black font-bold py-4 rounded-xl uppercase tracking-widest transition-all disabled:opacity-50 text-xl shadow-[0_0_20px_rgba(57,255,20,0.3)] hover:shadow-[0_0_30px_rgba(57,255,20,0.5)] transform hover:scale-[1.01]"
                    >
                        {loading ? "Criando Liga..." : "Iniciar Draft 🚀"}
                    </button>
                </div>
            </div>
        </div>
    );
}

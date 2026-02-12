import React, { useEffect, useState } from 'react';
import axios from 'axios';
import {
    Phone,
    Clock,
    CheckCircle,
    XCircle,
    BarChart2,
    User,
    Calendar,
    MessageSquare
} from 'lucide-react';
import { format } from 'date-fns';
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer
} from 'recharts';
import clsx from 'clsx';

// Constants
const API_URL = 'http://localhost:8000';

function App() {
    const [calls, setCalls] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedCall, setSelectedCall] = useState(null);

    useEffect(() => {
        fetchCalls();
        const interval = setInterval(fetchCalls, 5000); // Poll every 5s
        return () => clearInterval(interval);
    }, []);

    const fetchCalls = async () => {
        try {
            const response = await axios.get(`${API_URL}/calls`);
            setCalls(response.data);
            setLoading(false);
        } catch (error) {
            console.error("Failed to fetch calls", error);
        }
    };

    // KPI Calculations
    const totalCalls = calls.length;
    const interestedLeads = calls.filter(c => c.analysis?.is_interested).length;
    const conversionRate = totalCalls > 0 ? Math.round((interestedLeads / totalCalls) * 100) : 0;
    const avgDuration = calls.length > 0
        ? Math.round(calls.reduce((acc, curr) => {
            const start = new Date(curr.start_time).getTime();
            const end = curr.end_time ? new Date(curr.end_time).getTime() : new Date().getTime();
            return acc + (end - start);
        }, 0) / calls.length / 1000)
        : 0;

    // Chart Data
    const chartData = [
        { name: 'Interested', value: interestedLeads },
        { name: 'Not Interested', value: totalCalls - interestedLeads },
    ];

    return (
        <div className="min-h-screen bg-gray-50 text-gray-900 font-sans">
            {/* Header */}
            <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <div className="bg-indigo-600 p-2 rounded-lg">
                            <Phone className="w-6 h-6 text-white" />
                        </div>
                        <h1 className="text-xl font-bold text-gray-900">Voice AI Dashboard</h1>
                    </div>
                    <div className="text-sm text-gray-500">
                        Last updated: {format(new Date(), 'HH:mm:ss')}
                    </div>
                </div>
            </header>

            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* KPI Cards */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                    <KpiCard
                        title="Total Calls"
                        value={totalCalls}
                        icon={<Phone className="text-indigo-600" />}
                    />
                    <KpiCard
                        title="Interested Leads"
                        value={interestedLeads}
                        icon={<CheckCircle className="text-green-600" />}
                        trend={conversionRate + "% conversion"}
                    />
                    <KpiCard
                        title="Avg Duration"
                        value={`${avgDuration}s`}
                        icon={<Clock className="text-blue-600" />}
                    />
                    <KpiCard
                        title="Active Campaigns"
                        value="1"
                        icon={<BarChart2 className="text-purple-600" />}
                    />
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    {/* Main List */}
                    <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center bg-gray-50">
                            <h2 className="text-lg font-semibold text-gray-800">Recent Calls</h2>
                        </div>
                        <div className="overflow-y-auto max-h-[600px]">
                            {loading ? (
                                <div className="p-8 text-center text-gray-500">Loading calls...</div>
                            ) : (
                                <table className="min-w-full divide-y divide-gray-200">
                                    <thead className="bg-gray-50 sticky top-0">
                                        <tr>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Time</th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Lead Score</th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Summary</th>
                                        </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-gray-200">
                                        {calls.map((call) => (
                                            <tr
                                                key={call.id}
                                                onClick={() => setSelectedCall(call)}
                                                className={clsx(
                                                    "cursor-pointer hover:bg-indigo-50 transition-colors",
                                                    selectedCall?.id === call.id ? "bg-indigo-50" : ""
                                                )}
                                            >
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <StatusBadge status={call.analysis?.is_interested ? "interested" : "not_interested"} />
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                    {format(new Date(call.start_time), 'MMM d, HH:mm')}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <div className="flex items-center">
                                                        <div className="w-16 bg-gray-200 rounded-full h-2 mr-2">
                                                            <div
                                                                className="bg-indigo-600 h-2 rounded-full"
                                                                style={{ width: `${(call.analysis?.lead_score || 0) * 10}%` }}
                                                            ></div>
                                                        </div>
                                                        <span className="text-sm text-gray-600">{call.analysis?.lead_score || '-'}</span>
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4 text-sm text-gray-500 max-w-xs truncate">
                                                    {call.analysis?.summary || "No analysis yet..."}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            )}
                        </div>
                    </div>

                    {/* Detail View */}
                    <div className="lg:col-span-1">
                        {selectedCall ? (
                            <div className="bg-white rounded-xl shadow-sm border border-gray-200 h-full flex flex-col sticky top-24">
                                <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
                                    <h2 className="text-lg font-semibold text-gray-800">Call Details</h2>
                                </div>
                                <div className="p-6 flex-1 overflow-y-auto max-h-[600px]">
                                    <div className="mb-6">
                                        <h3 className="text-xs font-uppercase text-gray-500 tracking-wider mb-2">Analysis</h3>
                                        <div className="bg-gray-50 p-4 rounded-lg border border-gray-100">
                                            <div className="flex justify-between items-center mb-2">
                                                <span className="text-sm font-medium text-gray-700">Interest Level</span>
                                                <StatusBadge status={selectedCall.analysis?.is_interested ? "interested" : "not_interested"} />
                                            </div>
                                            <p className="text-sm text-gray-600 mb-2">
                                                <span className="font-semibold">Loan Type:</span> {selectedCall.analysis?.loan_type || "N/A"}
                                            </p>
                                            <p className="text-sm text-gray-600 italic">
                                                "{selectedCall.analysis?.summary}"
                                            </p>
                                        </div>
                                    </div>

                                    <div>
                                        <h3 className="text-xs font-uppercase text-gray-500 tracking-wider mb-4 flex items-center gap-2">
                                            <MessageSquare size={14} /> Transcript
                                        </h3>
                                        <div className="space-y-4">
                                            {selectedCall.transcript && Array.isArray(selectedCall.transcript) ? (
                                                selectedCall.transcript.map((msg, idx) => (
                                                    <div key={idx} className={clsx(
                                                        "flex flex-col max-w-[90%] rounded-lg p-3 text-sm",
                                                        msg.role === "user"
                                                            ? "bg-indigo-100 self-end ml-auto text-indigo-900"
                                                            : "bg-gray-100 self-start mr-auto text-gray-800"
                                                    )}>
                                                        <span className="text-xs opacity-50 mb-1 capitalize">{msg.role}</span>
                                                        {/* Handle complex message objects from Pipecat which might be dicts with 'parts' */}
                                                        {msg.parts ? (
                                                            msg.parts.map((p, i) => <span key={i}>{p.text}</span>)
                                                        ) : (
                                                            <span>{msg.content || JSON.stringify(msg)}</span>
                                                        )}
                                                    </div>
                                                ))
                                            ) : (
                                                <div className="text-gray-400 text-sm italic">No transcript available</div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="bg-gray-50 border-2 border-dashed border-gray-200 rounded-xl h-64 flex items-center justify-center text-gray-400">
                                Select a call to view details
                            </div>
                        )}
                    </div>
                </div>
            </main>
        </div>
    );
}

// Components
const KpiCard = ({ title, value, icon, trend }) => (
    <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
        <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-gray-500">{title}</h3>
            <div className="p-2 bg-gray-50 rounded-lg">{icon}</div>
        </div>
        <div className="flex items-end gap-2">
            <div className="text-2xl font-bold text-gray-900">{value}</div>
            {trend && <div className="text-xs text-green-600 font-medium mb-1">{trend}</div>}
        </div>
    </div>
);

const StatusBadge = ({ status }) => {
    const styles = {
        interested: "bg-green-100 text-green-800 border-green-200",
        not_interested: "bg-red-100 text-red-800 border-red-200",
        pending: "bg-yellow-100 text-yellow-800 border-yellow-200",
    };

    return (
        <span className={clsx(
            "px-2.5 py-0.5 rounded-full text-xs font-medium border",
            styles[status] || styles.pending
        )}>
            {status === "interested" ? "Interested" : "Not Interested"}
        </span>
    );
};

export default App;

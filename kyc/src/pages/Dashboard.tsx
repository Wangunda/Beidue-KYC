import React, { useState } from "react";
import { User, AlertTriangle, CheckCircle, XCircle, Shield, Search, Plus, Eye, Download, FileText, Users } from "lucide-react";
import type { Customer } from "../contexts/type";

interface DashboardProps {
  customers: Customer[];
  setActiveTab: (tab: "dashboard" | "newKYC" | "customerDetail") => void;
  setSelectedCustomer: (customer: Customer) => void;
  onSelectCustomer: (customer: Customer) => void;
}



const Dashboard: React.FC<DashboardProps> = ({ customers, setActiveTab, setSelectedCustomer }) => {
  const [searchTerm, setSearchTerm] = useState("");
    // Simple derived stats
  const total = customers.length;
  const approved = customers.filter((c) => c.status === "approved").length;
  const pending = customers.filter((c) => c.status === "pending").length;
  const rejected = customers.filter((c) => c.status === "rejected").length;
  const highRisk = customers.filter((c) => c.riskLevel === "high").length;

  const riskLevelColor = (level: string) => {
    switch (level) {
      case "low": return "text-green-600 bg-green-100";
      case "medium": return "text-yellow-600 bg-yellow-100";
      case "high": return "text-red-600 bg-red-100";
      default: return "text-gray-600 bg-gray-100";
    }
  };

  const statusColor = (status: string) => {
    switch (status) {
      case "approved": return "text-green-600 bg-green-100";
      case "pending": return "text-yellow-600 bg-yellow-100";
      case "rejected": return "text-red-600 bg-red-100";
      case "review": return "text-blue-600 bg-blue-100";
      default: return "text-gray-600 bg-gray-100";
    }
  };

  const filteredCustomers = customers.filter(
    (customer) =>
      customer.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      customer.email.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const stats = {
    total: customers.length,
    pending: customers.filter((c) => c.status === "pending").length,
    approved: customers.filter((c) => c.status === "approved").length,
    rejected: customers.filter((c) => c.status === "rejected").length,
    highRisk: customers.filter((c) => c.riskLevel === "high").length,
  };

    function onSelectCustomer(customer: Customer): void {
        throw new Error("Function not implemented.");
    }

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
        <StatCard
          title="Total Customers"
          value={total}
          icon={<Users className="w-6 h-6 text-blue-600" />}
        />
        <StatCard
          title="Approved"
          value={approved}
          icon={<Shield className="w-6 h-6 text-green-600" />}
        />
        <StatCard
          title="Pending"
          value={pending}
          icon={<FileText className="w-6 h-6 text-yellow-600" />}
        />
        <StatCard
          title="Rejected"
          value={rejected}
          icon={<AlertTriangle className="w-6 h-6 text-red-600" />}
        />
        <StatCard
          title="High Risk"
          value={highRisk}
          icon={<Shield className="w-6 h-6 text-orange-600" />}
        />
      </div>

      {/* Customers Table */}
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <div className="px-6 py-4 border-b">
          <h2 className="text-lg font-semibold">Customers</h2>
        </div>
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Email</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Risk</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              <th className="px-6 py-3"></th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {customers.map((customer) => (
              <tr key={customer.id} className="hover:bg-gray-50 cursor-pointer">
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{customer.name}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{customer.email}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{customer.type}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                      customer.riskLevel === "high"
                        ? "bg-red-100 text-red-800"
                        : customer.riskLevel === "medium"
                        ? "bg-yellow-100 text-yellow-800"
                        : "bg-green-100 text-green-800"
                    }`}
                  >
                    {customer.riskLevel}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                      customer.status === "approved"
                        ? "bg-green-100 text-green-800"
                        : customer.status === "pending"
                        ? "bg-yellow-100 text-yellow-800"
                        : "bg-red-100 text-red-800"
                    }`}
                  >
                    {customer.status}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <button
                    onClick={() => onSelectCustomer(customer)}
                    className="text-indigo-600 hover:text-indigo-900"
                  >
                    View
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// Small stat card component
interface StatCardProps {
  title: string;
  value: number;
  icon: React.ReactNode;
}

const StatCard: React.FC<StatCardProps> = ({ title, value, icon }) => (
  <div className="bg-white p-4 rounded-lg shadow flex items-center space-x-4">
    <div className="p-3 rounded-full bg-gray-100">{icon}</div>
    <div>
      <p className="text-sm text-gray-500">{title}</p>
      <p className="text-xl font-semibold">{value}</p>
    </div>
  </div>
);

export default Dashboard;

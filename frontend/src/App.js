import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider } from "@/contexts/AuthContext";
import { ThemeProvider } from "@/contexts/ThemeContext";
import ProtectedRoute from "@/components/ProtectedRoute";
import AppLayout from "@/components/layout/AppLayout";
import LoginPage from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import Customers from "@/pages/Customers";
import Products from "@/pages/Products";
import Quotations from "@/pages/Quotations";
import QuotationEditor from "@/pages/QuotationEditor";
import Invoices from "@/pages/Invoices";
import InvoiceEditor from "@/pages/InvoiceEditor";
import Projects from "@/pages/Projects";
import ProjectDetail from "@/pages/ProjectDetail";
import Accounts from "@/pages/Accounts";
import Licenses from "@/pages/Licenses";
import LogiLicense from "@/pages/LogiLicense";
import LogiLicenseDetail from "@/pages/LogiLicenseDetail";
import Users from "@/pages/Users";
import Settings from "@/pages/Settings";
import ActivityLogs from "@/pages/ActivityLogs";

const P = ({ name, children }) => <ProtectedRoute permission={name}>{children}</ProtectedRoute>;

function App() {
  return (
    <ThemeProvider><AuthProvider><BrowserRouter>
      <Toaster richColors position="top-right" closeButton />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
          <Route index element={<Dashboard />} />
          <Route path="customers" element={<P name="customers"><Customers /></P>} />
          <Route path="products" element={<P name="products"><Products /></P>} />
          <Route path="quotations" element={<P name="quotations"><Quotations /></P>} />
          <Route path="quotations/:id" element={<P name="quotations"><QuotationEditor /></P>} />
          <Route path="quotations/new" element={<P name="quotations"><QuotationEditor /></P>} />
          <Route path="invoices" element={<P name="invoices"><Invoices /></P>} />
          <Route path="invoices/:id" element={<P name="invoices"><InvoiceEditor /></P>} />
          <Route path="invoices/new" element={<P name="invoices"><InvoiceEditor /></P>} />
          <Route path="projects" element={<P name="projects"><Projects /></P>} />
          <Route path="projects/:id" element={<P name="projects"><ProjectDetail /></P>} />
          <Route path="accounts" element={<P name="accounts"><Accounts /></P>} />
          <Route path="licenses" element={<P name="licenses"><Licenses /></P>} />
          <Route path="logi-license" element={<P name="logi_license"><LogiLicense /></P>} />
          <Route path="logi-license/:id" element={<P name="logi_license"><LogiLicenseDetail /></P>} />
          <Route path="activity-logs" element={<P name="activity_logs"><ActivityLogs /></P>} />
          <Route path="users" element={<ProtectedRoute adminOnly><Users /></ProtectedRoute>} />
          <Route path="settings" element={<ProtectedRoute adminOnly><Settings /></ProtectedRoute>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter></AuthProvider></ThemeProvider>
  );
}
export default App;

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

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Toaster richColors position="top-right" closeButton />
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <AppLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Dashboard />} />
              <Route path="customers" element={<Customers />} />
              <Route path="products" element={<Products />} />
              <Route path="quotations" element={<Quotations />} />
              <Route path="quotations/:id" element={<QuotationEditor />} />
              <Route path="quotations/new" element={<QuotationEditor />} />
              <Route path="invoices" element={<Invoices />} />
              <Route path="invoices/:id" element={<InvoiceEditor />} />
              <Route path="invoices/new" element={<InvoiceEditor />} />
              <Route path="projects" element={<Projects />} />
              <Route path="projects/:id" element={<ProjectDetail />} />
              <Route
                path="accounts"
                element={
                  <ProtectedRoute adminOnly>
                    <Accounts />
                  </ProtectedRoute>
                }
              />
              <Route path="licenses" element={<Licenses />} />
              <Route
                path="logi-license"
                element={
                  <ProtectedRoute adminOnly>
                    <LogiLicense />
                  </ProtectedRoute>
                }
              />
              <Route
                path="logi-license/:id"
                element={
                  <ProtectedRoute adminOnly>
                    <LogiLicenseDetail />
                  </ProtectedRoute>
                }
              />
              <Route
                path="activity-logs"
                element={
                  <ProtectedRoute adminOnly>
                    <ActivityLogs />
                  </ProtectedRoute>
                }
              />
              <Route
                path="users"
                element={
                  <ProtectedRoute adminOnly>
                    <Users />
                  </ProtectedRoute>
                }
              />
              <Route
                path="settings"
                element={
                  <ProtectedRoute adminOnly>
                    <Settings />
                  </ProtectedRoute>
                }
              />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;

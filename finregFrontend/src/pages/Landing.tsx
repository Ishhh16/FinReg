import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useNavigate } from "react-router-dom";
import { Shield, Search, FileText, AlertTriangle } from "lucide-react";

const Landing = () => {
  const navigate = useNavigate();

  const features = [
    {
      icon: Shield,
      title: "AI Compliance Assessment",
      description: "Analyze corporate documents against statutory requirements using a Retrieval-Augmented Generation (RAG) pipeline."
    },
    {
      icon: Search,
      title: "Evidence-Backed Regulatory Citations",
      description: "Retrieve relevant provisions from the Companies Act, 2013 with page-level citations and semantic matching."
    },
    {
      icon: FileText,
      title: "Executive Compliance Reports",
      description: "Generate professional audit-ready compliance reports containing findings, gap analysis, supporting evidence, risk assessment, and remediation recommendations."
    },
    {
      icon: AlertTriangle,
      title: "Compliance Risk Detection",
      description: "Automatically identify compliance gaps, regulatory risks, and missing disclosures with confidence scoring and actionable recommendations."
    }
  ];

  return (
    <div className="min-h-screen animated-bg flex flex-col justify-center">
      {/* Hero Section */}
      <div className="container mx-auto px-4 pt-16 pb-12">
        <div className="text-center animate-slide-up">
          <div className="flex flex-col items-center justify-center mb-8">
            <img 
              src="/finreg-logo.svg" 
              alt="FinReg Logo" 
              className="h-16 md:h-20 mb-3"
            />
            <span className="text-xs font-bold uppercase tracking-widest text-slate-500 bg-slate-100 px-3.5 py-1.5 rounded-full border border-slate-200 shadow-sm">
              AI-Powered Compliance Intelligence
            </span>
          </div>
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold mb-6 tracking-tight text-primary leading-tight max-w-4xl mx-auto">
            Regulatory Compliance Intelligence Platform
          </h1>
          <p className="text-sm md:text-base text-slate-500 mb-12 max-w-4xl mx-auto font-medium leading-relaxed">
            AI-powered analysis of annual reports, board reports, financial statements, and corporate governance documents against the Companies Act, 2013 using Retrieval-Augmented Generation (RAG), semantic search, and evidence-backed AI reasoning.
          </p>
        </div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-16 max-w-5xl mx-auto">
          {features.map((feature, index) => (
            <Card
              key={index}
              className="glass glass-hover p-6 border border-slate-200 shadow-sm rounded-xl bg-white animate-slide-up"
              style={{ animationDelay: `${index * 0.1}s` }}
            >
              <div className="flex items-start space-x-4">
                <div className="bg-slate-100 p-3 rounded-lg flex-shrink-0">
                  <feature.icon className="w-6 h-6 text-slate-900" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900 mb-1.5">{feature.title}</h3>
                  <p className="text-xs md:text-sm text-slate-500 leading-relaxed">{feature.description}</p>
                </div>
              </div>
            </Card>
          ))}
        </div>

        {/* CTA Button */}
        <div className="text-center animate-slide-up" style={{ animationDelay: '0.4s' }}>
          <Button
            onClick={() => navigate('/dashboard')}
            className="glow-button text-base px-10 py-5 h-auto rounded-xl font-bold bg-slate-900 hover:bg-slate-800 text-white"
          >
            Enter Dashboard
          </Button>
        </div>
      </div>
    </div>
  );
};

export default Landing;
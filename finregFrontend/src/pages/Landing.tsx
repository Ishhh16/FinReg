import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useNavigate } from "react-router-dom";
import { Shield, Search, FileText, AlertTriangle } from "lucide-react";

const Landing = () => {
  const navigate = useNavigate();

  const features = [
    {
      icon: Shield,
      title: "Automated Compliance Analysis",
      description: "AI-powered analysis of financial documents against current regulations"
    },
    {
      icon: Search,
      title: "Direct Regulatory Citations",
      description: "Instant access to relevant regulatory requirements and citations"
    },
    {
      icon: FileText,
      title: "Interactive Reports",
      description: "Comprehensive compliance reports with actionable insights"
    },
    {
      icon: AlertTriangle,
      title: "Significant Gap Alerts",
      description: "Real-time alerts for critical compliance gaps and violations"
    }
  ];

  return (
    <div className="min-h-screen animated-bg">
      {/* Hero Section */}
      <div className="container mx-auto px-4 pt-20 pb-16">
        <div className="text-center animate-slide-up">
          <div className="flex items-center justify-center mb-6">
            <img 
              src="/finreg-logo.svg" 
              alt="FinReg Logo" 
              className="h-16 md:h-20"
            />
          </div>
          <h1 className="text-5xl md:text-7xl font-bold mb-6 tracking-tight text-white">
            Financial Regulation Made Simple
          </h1>
          <p className="text-xl md:text-2xl text-muted-foreground mb-12 max-w-3xl mx-auto">
            AI-Powered Compliance Analysis & Regulatory Citations
          </p>
        </div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-16 max-w-6xl mx-auto">
          {features.map((feature, index) => (
            <Card
              key={index}
              className="glass glass-hover p-8 border-0 animate-slide-up"
              style={{ animationDelay: `${index * 0.1}s` }}
            >
              <div className="flex items-start space-x-4">
                <div className="bg-primary/10 p-3 rounded-lg">
                  <feature.icon className="w-6 h-6 text-primary" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold mb-2">{feature.title}</h3>
                  <p className="text-muted-foreground">{feature.description}</p>
                </div>
              </div>
            </Card>
          ))}
        </div>

        {/* CTA Button */}
        <div className="text-center animate-slide-up" style={{ animationDelay: '0.5s' }}>
          <Button
            variant="hero"
            size="lg"
            onClick={() => navigate('/dashboard')}
            className="glow-button text-lg px-12 py-6 rounded-2xl font-semibold"
          >
            Get Started
          </Button>
        </div>
      </div>
    </div>
  );
};

export default Landing;
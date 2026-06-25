import React from 'react';
import { Case } from '@/types/case';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Calendar, MapPin, Users, FileText } from 'lucide-react';
import { Link } from 'react-router-dom';
import { cn } from '@/lib/utils';

interface CaseCardProps {
  caseData: Case;
}

const statusColors: Record<string, string> = {
  'Under Investigation': 'bg-warning/10 text-warning border-warning/20',
  'Pending Trial': 'bg-info/10 text-info border-info/20',
  'Closed': 'bg-muted text-muted-foreground border-muted',
  'Convicted': 'bg-success/10 text-success border-success/20',
  'Charge Sheet Filed': 'bg-info/10 text-info border-info/20',
  'Arrested': 'bg-destructive/10 text-destructive border-destructive/20',
  'Bail Granted': 'bg-success/10 text-success border-success/20',
  'Acquitted': 'bg-success/10 text-success border-success/20',
  'Archived': 'bg-muted text-muted-foreground border-muted',
};

export const CaseCard: React.FC<CaseCardProps> = ({ caseData }) => {
  return (
    <Link to={`/case/${caseData.id}`}>
      <Card className="group h-full transition-all duration-200 hover:shadow-elevated hover:border-primary/20 cursor-pointer">
          <CardHeader className="pb-3">
            <div className="flex items-start justify-between gap-2">
              <div className="space-y-1">
                <h3 className="font-display font-semibold text-lg group-hover:text-primary transition-colors">
                  {caseData.caseNumber}
                </h3>
                <p className="text-sm text-muted-foreground">{caseData.district}</p>
              </div>
              <Badge variant="outline" className={cn('shrink-0', statusColors[caseData.status] || 'bg-muted text-muted-foreground border-muted')}>
                {caseData.status}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-1.5">
              {caseData.lawSections.slice(0, 3).map((section) => (
                <Badge key={section} variant="secondary" className="text-xs">
                  {section}
                </Badge>
              ))}
              {caseData.lawSections.length > 3 && (
                <Badge variant="secondary" className="text-xs">
                  +{caseData.lawSections.length - 3}
                </Badge>
              )}
            </div>

            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2 text-muted-foreground">
                <MapPin className="h-4 w-4 shrink-0" />
                <span className="truncate">{caseData.sceneOfCrime}</span>
              </div>
              <div className="flex items-center gap-2 text-muted-foreground">
                <Calendar className="h-4 w-4 shrink-0" />
                <span>Offence: {new Date(caseData.dateOfOffence).toLocaleDateString()}</span>
              </div>
              <div className="flex items-center gap-2 text-muted-foreground">
                <Users className="h-4 w-4 shrink-0" />
                <span>{caseData.accused.length} Accused</span>
              </div>
              <div className="flex items-center gap-2 text-muted-foreground">
                <FileText className="h-4 w-4 shrink-0" />
                <span>{caseData.evidence.length} Evidence Items</span>
              </div>
            </div>

            {caseData.accused.length > 0 && (
              <div className="pt-3 border-t border-border">
                <p className="text-xs text-muted-foreground mb-2">Primary Accused:</p>
                <p className="text-sm font-medium">{caseData.accused[0].name}</p>
                <p className="text-xs text-muted-foreground">
                  {caseData.accused[0].status}
                </p>
              </div>
            )}
          </CardContent>
        </Card>
    </Link>
  );
};
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import { FileText } from "lucide-react";

interface FileNameInputProps {
  fileName: string;
  extension: string;
  onChange: (name: string) => void;
}

export const FileNameInput = ({ fileName, extension, onChange }: FileNameInputProps) => {
  return (
    <div className="w-full space-y-2">
      <Label htmlFor="file-name" className="text-sm text-muted-foreground flex items-center gap-2">
        <FileText className="h-4 w-4" />
        File Name
      </Label>
      <div className="flex items-center gap-2">
        <Input
          id="file-name"
          type="text"
          value={fileName}
          onChange={(e) => onChange(e.target.value)}
          className="flex-1 bg-secondary border-border"
          placeholder="Enter custom file name"
          aria-label="Custom file name"
        />
        <span className="text-muted-foreground font-mono text-sm">.{extension}</span>
      </div>
    </div>
  );
};

import { AlertCircle, RefreshCw, Info } from "lucide-react";
import { motion } from "framer-motion";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { ErrorInfo } from "@/lib/errors";

interface ErrorCardProps {
  error: ErrorInfo;
  onRetry?: () => void;
  onDismiss?: () => void;
  variant?: "alert" | "card";
  showRetry?: boolean;
}

/**
 * ErrorCard Component
 * 
 * Displays detailed error information with title, message, and actionable guidance.
 * Supports both alert and card variants for different use cases.
 */
export const ErrorCard = ({
  error,
  onRetry,
  onDismiss,
  variant = "alert",
  showRetry = true,
}: ErrorCardProps) => {
  if (variant === "alert") {
    return (
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        transition={{ duration: 0.3 }}
      >
        <Alert variant="destructive" className="mb-4">
          <AlertCircle className="h-5 w-5" />
          <AlertTitle className="ml-2">{error.title}</AlertTitle>
          <AlertDescription className="ml-2 mt-2 space-y-2">
            <p>{error.message}</p>
            <div className="flex items-start gap-2 mt-3 p-3 bg-destructive/10 rounded-md border border-destructive/20">
              <Info className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <p className="text-sm">{error.action}</p>
            </div>
            {(showRetry && onRetry) || onDismiss ? (
              <div className="flex gap-2 mt-4">
                {showRetry && onRetry && (
                  <Button
                    onClick={onRetry}
                    variant="outline"
                    size="sm"
                    className="border-destructive/50 hover:bg-destructive/10"
                  >
                    <RefreshCw className="mr-2 h-4 w-4" />
                    Try Again
                  </Button>
                )}
                {onDismiss && (
                  <Button
                    onClick={onDismiss}
                    variant="ghost"
                    size="sm"
                    className="text-destructive hover:text-destructive hover:bg-destructive/10"
                  >
                    Dismiss
                  </Button>
                )}
              </div>
            ) : null}
          </AlertDescription>
        </Alert>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.3 }}
    >
      <Card className="border-destructive/50 bg-destructive/5">
        <CardHeader className="pb-3">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-full bg-destructive/10">
              <AlertCircle className="h-5 w-5 text-destructive" />
            </div>
            <div>
              <h3 className="font-semibold text-destructive">{error.title}</h3>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">{error.message}</p>
          <div className="flex items-start gap-2 p-3 bg-muted rounded-md border">
            <Info className="h-4 w-4 mt-0.5 flex-shrink-0 text-primary" />
            <p className="text-sm">{error.action}</p>
          </div>
        </CardContent>
        {(showRetry && onRetry) || onDismiss ? (
          <CardFooter className="flex gap-2 pt-0">
            {showRetry && onRetry && (
              <Button
                onClick={onRetry}
                variant="outline"
                size="sm"
                className="border-destructive/50 hover:bg-destructive/10"
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                Try Again
              </Button>
            )}
            {onDismiss && (
              <Button
                onClick={onDismiss}
                variant="ghost"
                size="sm"
              >
                Dismiss
              </Button>
            )}
          </CardFooter>
        ) : null}
      </Card>
    </motion.div>
  );
};

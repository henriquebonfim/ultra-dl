import { motion } from "framer-motion";
import { Heart } from "lucide-react";

export const Footer = () => {
  return (
    <motion.footer
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.6, delay: 0.5 }}
      className="w-full py-8 px-4 mt-16 border-t border-border"
    >
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <span>Powered by yt-dlp + ffmpeg</span>
          <span>•</span>
          <span className="flex items-center gap-1">
            Built with <Heart className="h-4 w-4 text-destructive inline fill-destructive" /> by UltraDL Team
          </span>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <a href="#" className="text-muted-foreground hover:text-primary transition-colors">
            Privacy Policy
          </a>
          <span className="text-muted-foreground">•</span>
          <a href="#" className="text-muted-foreground hover:text-primary transition-colors">
            Terms of Service
          </a>
        </div>
      </div>
    </motion.footer>
  );
};

import { motion } from "framer-motion";
import { Youtube } from "lucide-react";

export const Header = () => {
  return (
    <motion.header
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      className="w-full py-6 px-4"
    >
      <div className="max-w-6xl mx-auto flex items-center justify-center flex-col gap-2">
        <div className="flex items-center gap-3">
          <div className="relative">
            <Youtube className="h-10 w-10 text-primary" strokeWidth={2} />
            <div className="absolute inset-0 blur-xl opacity-50 bg-primary rounded-full" />
          </div>
          <h1 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
            UltraDL
          </h1>
        </div>
        <p className="text-muted-foreground text-sm md:text-base text-center">
          Download your favorite YouTube videos in any resolution.
        </p>
      </div>
    </motion.header>
  );
};

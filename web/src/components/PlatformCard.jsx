import { motion } from 'framer-motion';

function PlatformCard({ platform, index, onClick, disabled }) {
    return (
        <motion.button
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 * index }}
            whileHover={{ scale: disabled ? 1 : 1.03, y: disabled ? 0 : -8 }}
            whileTap={{ scale: disabled ? 1 : 0.98 }}
            onClick={onClick}
            disabled={disabled}
            className={`platform-card relative overflow-hidden rounded-2xl p-6 text-left
        glass ${platform.hoverGlow} hover:shadow-2xl
        transition-all duration-300 cursor-pointer
        ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
        group`}
        >
            {/* Gradient overlay on hover */}
            <div
                className={`absolute inset-0 bg-gradient-to-br ${platform.gradient} opacity-0 
          group-hover:opacity-10 transition-opacity duration-300`}
            />

            {/* Badge */}
            {platform.badge && (
                <div className="absolute top-4 right-4">
                    <span className="px-3 py-1 text-xs font-semibold rounded-full bg-gradient-to-r from-purple-500 to-pink-500 text-white shadow-lg">
                        {platform.badge}
                    </span>
                </div>
            )}

            {/* Icon */}
            <motion.div
                className="text-5xl mb-4"
                animate={{ y: [0, -5, 0] }}
                transition={{ duration: 2, repeat: Infinity, delay: index * 0.3 }}
            >
                {platform.icon}
            </motion.div>

            {/* Content */}
            <h3 className="text-2xl font-bold text-white mb-2 group-hover:text-purple-300 transition-colors">
                {platform.name}
            </h3>
            <p className="text-gray-400 text-sm mb-4">
                {platform.description}
            </p>

            {/* Formats */}
            <div className="flex flex-wrap gap-2">
                {platform.formats.map((format) => (
                    <span
                        key={format}
                        className="px-2 py-1 text-xs rounded-md bg-purple-900/50 text-purple-300 
              border border-purple-700/30"
                    >
                        {format.toUpperCase()}
                    </span>
                ))}
            </div>

            {/* Arrow indicator */}
            <motion.div
                className="absolute bottom-6 right-6 text-purple-400 opacity-0 group-hover:opacity-100 
          transition-opacity"
                animate={{ x: [0, 5, 0] }}
                transition={{ duration: 1.5, repeat: Infinity }}
            >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                </svg>
            </motion.div>
        </motion.button>
    );
}

export default PlatformCard;

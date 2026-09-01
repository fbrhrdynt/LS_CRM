export default function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="border border-dashed border-border py-16 px-6 text-center flex flex-col items-center gap-3">
      {Icon && (
        <div className="h-12 w-12 border border-border grid place-items-center">
          <Icon className="h-5 w-5 text-muted-foreground" strokeWidth={1.5} />
        </div>
      )}
      <div>
        <div className="font-display font-medium">{title}</div>
        {description && <div className="text-sm text-muted-foreground mt-1">{description}</div>}
      </div>
      {action}
    </div>
  );
}

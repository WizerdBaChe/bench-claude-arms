namespace BatchRenameStudio.Core;

public enum ApplyToMode { Name, NameAndExtension }
public enum SortMode { Name, Created, Modified }
public enum InsertPosition { Prefix, Suffix, Index }
public enum SeqPosition { Prefix, Suffix }
public enum CaseMode { Upper, Lower, Title }
public enum ExtensionMode { Lower, Upper, Set }
public enum ItemStatus { Ok, Collision, Unchanged, Invalid }

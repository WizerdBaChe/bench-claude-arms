namespace BatchRenameStudio.Core;

public readonly record struct NameParts(string Base, string Ext)
{
    public static NameParts Split(string fileName)
    {
        int dot = fileName.LastIndexOf('.');
        if (dot > 0)
        {
            return new NameParts(fileName.Substring(0, dot), fileName.Substring(dot + 1));
        }
        return new NameParts(fileName, "");
    }

    public string Join()
    {
        return Ext.Length > 0 ? Base + "." + Ext : Base;
    }
}
